from pydantic import BaseModel
from ..common_enums import EducationLevel, LearningOutcome, TypeOfActivity
from pydantic import BaseModel

class ActivityUtils(BaseModel):
    goal: str # "assess if the audience achieved " / "help the audience achieve "
    plus: str
    solution: str
    distractors: str
    easily_discardable_distractors: str

class GenerateActivityRequest(BaseModel):
    macro_subject: str
    topic: str
    education_level: EducationLevel
    learning_outcome: LearningOutcome
    material: str
    solutions_number: int
    distractors_number: int
    easily_discardable_distractors_number: int
    type: TypeOfActivity
    language: str = "English"
    model: str = "Gemini"

class GenerateActivityResponse(BaseModel):
    assignment: str
    plus: str
    solutions: list[str]
    distractors: list[str]
    easily_discardable_distractors: list[str]

class Activity(BaseModel):
    macro_subject: str
    topic: str
    education_level: EducationLevel
    learning_outcome: LearningOutcome
    material: str
    assignment: str
    plus: str
    solutions: list[str]
    distractors: list[str]
    easily_discardable_distractors: list[str]
    type: TypeOfActivity
    language: str = "English"

def generate_activity_prompt(request: GenerateActivityRequest):
   
   activity_utils: ActivityUtils = get_activity_utils(request.type, request.solutions_number, request.distractors_number, request.easily_discardable_distractors_number)
   prompt = f"""You are an {request.language} expert educator and instructional designer specialized in {request.macro_subject}. 
Your expertise lies in creating **structured, engaging, and pedagogically sound activities (including exercises, projects and in-class activities)**. 

### Task
Your task is to generate an {request.type.value} for the topic: **'{request.topic}'**, ensuring it aligns with best teaching practices for a **{request.education_level.value}** audience.  
The **main goal** is to {activity_utils.goal} **'{request.learning_outcome.value}'** on the topic.

### Activity Structure
Since you are highly organized, you will follow a structured approach to craft the activity. 
1. **Assignment**: A concise and explanatory description of what the audience is expected to do.
2. **Plus**: {activity_utils.plus}.
3. **Solution**: {activity_utils.solution}.
4. **Distractors**: {activity_utils.distractors}.
5. **Easily Discardable Distractors**: {activity_utils.easily_discardable_distractors}.

Now you can generate the activity (in {request.language}).
Remember to tune the difficulty for a {request.education_level.value} audience, so don't make it too easy, or the audience will be bored. 
Also adjust the depth of the topics acccordingly to the desired learning outcome.
"""
   return prompt

def get_activity_utils(activity_type: TypeOfActivity, solutions_number: int, distractors_number: int, easily_discardable_distractors_number: int) -> ActivityUtils | None:
    mapping = {
        # CHOICE
        TypeOfActivity.MULTIPLE_SELECT: (
            "assess if the audience achieved ",
            "A tip on how to approach the exercise",
            f"A list of all the {solutions_number} correct answers",
            f"A list of {distractors_number} distractors. The distractors are incorrect answers that are placed among the possible answers to confuse the audience",
            f"A list of {easily_discardable_distractors_number} easily discardable distractors. These are incorrect answers that are completely wrong and can thus be easily discarded by the audience",
        ),
        TypeOfActivity.MULTIPLE_CHOICE: (
            "assess if the audience achieved ",
            "A tip on how to approach the exercise",
            "(list of one element) The only possible correct answer",
            f"A list of {distractors_number} distractors. The distractors are incorrect answers that are placed among the possible answers to confuse the audience",
            f"A list of {easily_discardable_distractors_number} easily discardable distractors. These are incorrect answers that are completely wrong and can thus be easily discarded by the audience",
        ),
        TypeOfActivity.MATCHING: (
            "assess if the audience achieved ",
            f"The left column of the matching exercise, so the list of  list of {solutions_number} elements to be matched",
            f"The right column of the matching exercise, so the ordered list of {solutions_number} elements that match the left column",
            f"A list of {distractors_number} distractors. The distractors are incorrect answers that are placed among the possible answers in the right column to confuse the audience",
            f"A list of {easily_discardable_distractors_number} easily discardable distractors. These are incorrect answers that are completely wrong and can thus be easily discarded by the audience",
        ),
        TypeOfActivity.ORDERING: (
            "assess if the audience achieved ",
            f"Any eventual context or tip on how to approach the exercise",
            f"The ordered list of {solutions_number} elements ",
            f"A list of {distractors_number} distractors. The distractors are elements vaguely related to the topic, but that do not fit in the ordered list. They are placed among the original elements to confuse the audience",
            f"A list of {easily_discardable_distractors_number} easily discardable distractors. These are completely out of context elements that can be easily discarded by the audience",
        ),

        # QUESTION
        TypeOfActivity.TRUE_OR_FALSE: (
            "assess if the audience achieved ",
            "The statement or question to be evaluated as true or false",
            f"(list of one element) The correct answer. Either 'true' or 'false,' + an explanation of why the statement is false",
            f"A list of {distractors_number} common misconceptions that may lead the audience to evaluate the statement or question incorrectly",
            "here write 'empty'; this field is not used for this type of activity",
        ),
        TypeOfActivity.SHORT_ANSWER_QUESTION: (
            "assess if the audience achieved ",
            "The statement to be completed or question to be answered with a short answer",
            f"(list of one element) The correct short answer. From 1 to 4 words",
            f"A list of {distractors_number} common misconceptions that may lead the audience to respond incorrectly",
            "here write 'empty'; this field is not used for this type of activity",
        ),
        TypeOfActivity.OPEN_QUESTION: (
            "assess if the audience achieved ",
            "The question to be answered",
            f"The list of key concepts that should be included in the answer",
            f"A list of {distractors_number} common misconceptions that may lead the audience to respond incorrectly",
            "here write 'empty'; this field is not used for this type of activity",
        ),
        TypeOfActivity.CODING: (
            "assess if the audience achieved ",
            "A complete and working code that does everything required in the assignment",
            f"The list of key concepts or functions that should be implemented in the code",
            f"A list of {distractors_number} too high level libraries or shortcuts that the audience should not use",
            "here write 'empty'; this field is not used for this type of activity",
        ),

        # FILL_IN_THE_BLANKS
        TypeOfActivity.FILL_IN_THE_BLANKS: (
            "assess if the audience achieved ",
            f"The text to be filled in. It should include {solutions_number} blanks",
            f"The ordered list of {solutions_number} elements that should be filled in the blanks",
            f"A list of {distractors_number} distractors. The distractors are incorrect elements that are placed among the possible answers to confuse the audience.",
            f"A list of {easily_discardable_distractors_number} easily discardable distractors. These are incorrect answers that are completely wrong and can thus be easily discarded by the audience.",
        ),

        # THEORETICAL
        TypeOfActivity.ESSAY: (
            "assess if the audience achieved ",
            "The essay topic that the audience should write about. It should be complete and coherent",
            "The list of key concepts that should be included in the essay",
            "here write 'empty'; this field is not used for this type of activity",
            "here write 'empty'; this field is not used for this type of activity",
        ),
        TypeOfActivity.KNOWLEDGE_EXPOSITION: (
            "assess if the audience achieved ",
            "The topic that the audience should expose. It should be a detailed description of what is expected",
            "The list of key concepts that should be included in the exposition",
            "here write 'empty'; this field is not used for this type of activity",
            "here write 'empty'; this field is not used for this type of activity",
        ),
        TypeOfActivity.DEBATE: (
            "help the audience achieve ",
            "The topic that the audience should debate. It should contain a series of questions to reason about",
            f"The list of {solutions_number} possible key arguments and counterarguments that could be included in the debate",
            f"A list of {distractors_number} concepts or arguments related to the topic, that are diffused in common believes, but are not supported by evidence and/or are not usable in this debate for some reasons",
            f"A list of {easily_discardable_distractors_number} concepts or arguments that the audience could, but should never reach as they are too drastic, irrelevant or even completely wrong",
        ),
        TypeOfActivity.BRAINSTORMING: (
            "help the audience achieve ",
            "The general topic that the audience should brainstorm. It should contain one question to reason about",
            f"A list of {solutions_number} hints and/or questions to help the brainstorming",
            f"A list of {distractors_number} approaches or arguments related to the topic, that are diffused in common believes, but are not supported by evidence and/or are not usable in this debate for some reasons",
            f"A list of {easily_discardable_distractors_number} concepts or arguments that the audience could, but should never reach as they are too drastic, irrelevant or even completely wrong",
        ),
        TypeOfActivity.GROUP_DISCUSSION: (
            "help the audience achieve ",
            "The topic that the audience should discuss together. It should contain a series of generic questions to reason about",
            "here write 'empty'; this field is not used for this type of activity",
            "here write 'empty'; this field is not used for this type of activity",
            "here write 'empty'; this field is not used for this type of activity",        
        ),
        TypeOfActivity.SIMULATION: (
            "help the audience achieve ",
            "The topic that will be simulated. Provide description of the context and the starting situation",
            f"A list of {solutions_number} characters to be simulated",
            f"A list of {distractors_number} approaches or arguments related to the topic, that are diffused in common believes, but are not supported by evidence and/or are not usable in this simulation for some reasons",
            f"A list of {easily_discardable_distractors_number} concepts or arguments that the audience could, but should never reach as they are too drastic, irrelevant or even completely wrong",
        ),
        TypeOfActivity.INQUIRY_BASED_LEARNING: (
        "help the audience achieve ",
        "A question or problem that will guide the audience's investigation",
        f"A list of {solutions_number} potential areas of investigation or resources to explore",
        f"A list of {distractors_number} common misconceptions or less fruitful avenues of inquiry",
        "here write 'empty'; this field is not used for this type of activity",
        ),

        # PRACTICAL
        TypeOfActivity.NON_WRITTEN_MATERIAL_ANALYSIS: (
            "assess if the audience achieved ",
            "Brief description of the non-written material (e.g., a picture, a graph, a sound recording) and the specific aspects to analyze",
            f"A list of the {solutions_number} most important interpretations or features to identify",
            f"A list of {distractors_number} plausible but incorrect interpretations or less important details",
            f"A list of {easily_discardable_distractors_number} completely irrelevant or nonsensical interpretations",
        ),
        TypeOfActivity.NON_WRITTEN_MATERIAL_PRODUCTION: (
            "assess if the audience achieved ",
            "Description of the non-written material to be produced (e.g., a drawing, a presentation, a short skit) and the communication goal",
            f"A list of the {solutions_number} most important key elements or features that the produced material should include",
            f"A list of {distractors_number} common mistakes or less effective ways to present the information",
            "here write 'empty'; this field is not used for this type of activity",
        ),
        TypeOfActivity.CASE_STUDY_ANALYSIS: (
            "help the audience achieve ",
            "A description of the case study, including relevant background information and events",
            f"A list of the {solutions_number} major problems or factors to consider in the specific case study",
            f"A list of {distractors_number} less relevant details or common misunderstandings of similar generic case studies",
            "here write 'empty'; this field is not used for this type of activity",
        ),
        TypeOfActivity.PROJECT_BASED_LEARNING: (
            "help the audience achieve ",
            "A description of the project goal and any specific requirements or constraints",
            f"A list of {solutions_number} key stages or milestones for successful project completion",
            f"A list of {distractors_number} common challenges or less effective approaches to the project",
            "here write 'empty'; this field is not used for this type of activity",
        ),
        TypeOfActivity.PROBLEM_SOLVING_ACTIVITY: (
            "assess if the audience achieved ",
            "A clear description of the problem to be solved, including any necessary information or constraints",
            f"A list of {solutions_number} possible and effective solutions to the problem",
            f"A list of {distractors_number} plausible but ultimately ineffective or inefficient solutions",
            f"A list of {easily_discardable_distractors_number} completely incorrect or illogical attempts to solve the problem",
        ),
    }
    activity_info = mapping.get(activity_type)
    if activity_info:
        return ActivityUtils(
            goal=activity_info[0],
            plus=activity_info[1],
            solution=activity_info[2],
            distractors=activity_info[3],
            easily_discardable_distractors=activity_info[4],
        )
    return None

"""Test text:
{
  "macro_subject": "History",
  "topic": "The Fall of the Western Roman Empire",
  "education_level": "high school",
  "learning_outcome": "the ability to recall or recognize simple facts and definitions",
  "material": "a short text describing the reasons for the fall of Rome",
  "solutions_number": 3,
  "distractors_number": 4,
  "easily_discardable_distractors_number": 2,
  "type": "brainstorming",
  "language": "Italian",
  "model": "gemini"
}
"""

