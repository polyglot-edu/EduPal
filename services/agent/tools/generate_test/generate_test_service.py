import random
from fastapi import UploadFile as FastapiUploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile
from services.agent.grounding.analyse_material.analyse_material_service import analysis
from services.agent.grounding.analyse_material.analyse_material_utils import AnalyseMaterialRequest
from services.agent.grounding.vector_search_retrieval.vector_search_service import vector_search_with_filter
from services.agent.grounding.vector_search_retrieval.vector_search_utils import VectorSearchResults
from services.agent.orchestrator.chat.chat_utils import Resource
from services.agent.orchestrator.chat.upload_service import check_file, semantic_chunking
from services.agent.tools.generate_activity.generate_activity_utils import Activity, ActivityParams, GenerateActivityRequest, GeneratedActivity, generate_activity_prompt
from services.agent.utils.common_enums import get_exercises
from services.llm_integration.llm_interface import get_llm
from .generate_test_utils import GenerateTestRequest, TopicParams

async def create_test(request: GenerateTestRequest):
    llm = get_llm(request.model)
    ext_result: tuple[list[Resource], list[TopicParams]] = ([], [])
    try:
        if request.material:
            ext_result = await get_resources(request)
        # if there are no topics, check if there are materials
        if not request.topics and not request.material:
            raise ValueError("Either topics or materials must be provided.")
        
        # if there are exercises...
        if len(request.exercises) > 0:
            # if there are topics, choose which topic to bind with each exercise
            if request.topics:
                # if some topics are associated with exercises, chek if those exercises appear in the exercises list, and eventually remove them
                for topic in request.topics:
                    if len(topic.exercise_params) > 0:
                        for exercise in topic.exercise_params:
                            if exercise in request.exercises:
                                request.exercises.remove(exercise)
            else: # in this case topics is None and materials is not None
                request.topics.extend(ext_result[1])  # add the topics extracted from the material to the request.topics
                request.material = ext_result[0]  # update the request.material with the resources extracted from the material
            # now randomly choose the topics for the remaining exercises
            if len(request.exercises) > 0:
                for exercise in request.exercises:
                    single_topic: TopicParams = random.choice(request.topics)
                    single_topic.exercise_params.append(exercise)
            # keep only the topics that have at least one exercise
            request.topics = [topic for topic in request.topics if topic.exercise_params is not None and len(topic.exercise_params) > 0]

        else:  # if there are no exercises, check if there are topics
            if request.topics is None or len(request.topics) == 0: # in this case topics is None and materials is not None
                request.topics.extend(ext_result[1])  # add the topics extracted from the material to the request.topics
                request.material = ext_result[0]  # update the request.material with the resources extracted from the material
            # now topics is not None and has at least one topic and material is a list of Resource
            # randomly generate a set of exercises param for each topic
            for topic in request.topics:
                if topic.exercise_params is None or len(topic.exercise_params) == 0:
                    topic.exercise_params = []
                    rand_type_of_exercise = random.choice(get_exercises())
                    rand_solutions_number = random.randint(1, 5)
                    rand_distractors_number = random.randint(1, 5)
                    rand_easily_discardable_distractors_number = random.randint(1, 5)
                    topic.exercise_params.append(
                        ActivityParams(
                            type=rand_type_of_exercise,
                            solutions_number=rand_solutions_number,
                            distractors_number=rand_distractors_number,
                            easily_discardable_distractors_number=rand_easily_discardable_distractors_number
                        )
                    )

        # now request.topics is not None and each topic has at least one exercise
        final_response: list[Activity] = [] # define the final response variable
        for topic in request.topics:
            if not request.material:
                string_material = "INDICATIONS FOR LLM: use your knowledge to decide what to base the exercise on"
            else: # if there are materials, use vector search to find the most relevant snippets for each topic
                string_material = ""
                if isinstance(request.material, list):
                    for res in request.material:
                        vs_results = vector_search_with_filter(
                            resource = res,
                            queries = [topic.topic_name],
                            score_threshold=0.5,
                            k = 3,
                        )
                        if vs_results:
                            for vs_result in vs_results:
                                string_material += vs_result.to_str()

            # map the information into the activity generation request
            single_request: GenerateActivityRequest = GenerateActivityRequest(
                macro_subject =request.macro_subject,
                topic = topic.topic_name,
                topic_explanation = topic.topic_explanation,
                education_level = request.education_level,
                learning_outcome = topic.learning_outcome,
                material = string_material,
                params = topic.exercise_params,
                language = request.language,
                model = request.model
            )
            # generate the exercises for that topic
            response: list[GeneratedActivity] = llm.generate_text(prompt=generate_activity_prompt(single_request), response_model=list[GeneratedActivity])
            #print("Response",response)
            #print("-"*100)
            if response is not None:
                print(response)
                final_act = Activity(
                    macro_subject=single_request.macro_subject,
                    topic=single_request.topic,
                    topic_explanation=single_request.topic_explanation,
                    education_level=single_request.education_level,
                    learning_outcome=single_request.learning_outcome,
                    material=single_request.material,
                    params=single_request.params,
                    generated_activities=response,
                    language=single_request.language,
                    model=single_request.model
                )
                final_response.append(final_act)

        return final_response

    except Exception as e:
        raise


async def get_resources(request: GenerateTestRequest)-> tuple[list[Resource], list[TopicParams]]:
    res_material: list[Resource] = []
    # if the material is not already of type Resource, extract it
    if not isinstance(request.material, list) and isinstance(request.material, (FastapiUploadFile, StarletteUploadFile)):
        extracted_resource: Resource = await extract_resource(request.material, request.model)
        if extracted_resource.analysis.topics is None or len(extracted_resource.analysis.topics) == 0:
            raise ValueError("No topics could be extracted from the provided materials.")
        res_material = [extracted_resource]
    else: # if the material is already a list of Resource
        res_material = request.material
    # if the material is empty, raise an error
    if res_material is None or len(res_material) == 0:
        raise ValueError("No material provided or no topics could be extracted from the provided materials.")

    final_topics: list[TopicParams] = [] # initialize the topics list
    # extract the topics from the resources and add them to the topics list
    for res in res_material:
        for analysis_topic in res.analysis.topics:
            final_topics.append(
                TopicParams(
                    topic_name=analysis_topic.topic,
                    topic_explanation=analysis_topic.explanation,
                    learning_outcome=request.learning_outcome,
                    exercise_params=[]
                )
            )
        # Now final_topics is not None and has at least one topic
    if not final_topics:
        raise ValueError("No topics could be extracted from the provided materials.")
    return res_material, final_topics
              

async def extract_resource(material: FastapiUploadFile | StarletteUploadFile, model: str) -> Resource:
    file = material
    url = None
    file_path: str = await check_file(file=file if file else None, url=url if url else None)
    # Analize the material
    request = AnalyseMaterialRequest(text=file_path, model=model)
    analysed_material = analysis(request)
    # Perform semantic chunking
    chunks = semantic_chunking(file_path)
    # Create Resource object from the chunks
    document = Resource(
        analysis=analysed_material,
        content=chunks
    )
    return document