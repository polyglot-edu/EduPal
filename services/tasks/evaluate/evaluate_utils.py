from pydantic import BaseModel
from ..common_enums import EducationLevel, LearningOutcome, TypeOfActivity
from pydantic import BaseModel

class ActivityUtils(BaseModel):
    goal: str # "assess if the audience achieved " / "help the audience achieve "
    solution: str
    correctness: str
    comment: str
    advice: str

class EvaluateRequest(BaseModel):
    macro_subject: str
    topic: str
    education_level: EducationLevel
    learning_outcome: LearningOutcome
    assignment: str
    answer: str
    solutions: list[str]
    type: TypeOfActivity
    language: str = "English"
    model: str = "Gemini"

class EvaluateResponse(BaseModel):
    correctness_percentage: int
    comment: str
    advice: str

class Evaluation(BaseModel):
    macro_subject: str
    topic: str
    education_level: EducationLevel
    learning_outcome: LearningOutcome
    assignment: str
    answer: str
    solutions: list[str]
    correctness_percentage: int
    comment: str
    advice: str
    type: TypeOfActivity
    language: str = "English"

def evaluate_prompt(request: EvaluateRequest):
   activity_utils: ActivityUtils = get_activity_utils(request.type, request.solutions)
   prompt = f"""You are an {request.language} expert educator specialized in {request.macro_subject}. 
Your expertise lies in evaluating and reviewing educational activities (including exercises, projects and in-class activities), and also in giving personalized and pedagociacally sound feedback to students.

### Task
Your task is to evaluate an {request.type.value} regarding the topic: **'{request.topic}'**.
You need to consider that the activity was meant for an **{request.education_level.value}** audience, and that its **main goal** was to {activity_utils.goal} **'{request.learning_outcome.value}'** on the topic.
{activity_utils.solution}

Assignment: {request.assignment}
Answer: {request.answer}

### Evaluation Structure
Since you are highly organized, you will follow a structured approach to evaluate the activity. 
1. **Correctness**: {activity_utils.correctness}
2. **Comment**: {activity_utils.comment}
3. **Advice**: {activity_utils.advice}

Now you can generate the Evaluation (in {request.language}).
Remember to calibrate the evaluation considering the general expectations you can have from a {request.education_level.value} audience. 
Also, consider that the activity was meant to achieve a specific learning outcome, so you should evaluate the activity based on how well it meets that goal. 
"""
   return prompt

def get_activity_utils(activity_type: TypeOfActivity, solutions: list[str]) -> ActivityUtils | None:
    mapping = {
        # CHOICE
        TypeOfActivity.MULTIPLE_SELECT: (
            "assess if the audience achieved ",
            f"To help you evaluate the answer, the correct elements are '{solutions}'.",
            "A percentage between 0 and 100 that represents the correctness of the answer.",
            "If correctness is not 100%, explain which were the correct elements and why.",
            "If needed, a suggestion for how to better approach this kind of activity in the future, or a general suggestion for how to approach the study of similar topics. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.MULTIPLE_CHOICE: (
            "assess if the audience achieved ",
            f"To help you evaluate the answer, the correct choice is '{solutions[0]}'.",
            "Either 'correct' or 'incorrect'.",
            "If 'incorrect', explain which was the correct choice and why.",
            "If needed, a suggestion for how to better approach this kind of activity in the future, or a general suggestion for how to approach the study of similar topics. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.MATCHING: (
            "assess if the audience achieved ",
            f"To help you evaluate the answer, the correct matches are '{solutions}'.",
            "The number of correctly placed elements in the list. For example, if the correct order is 'a, b, c', and the answer is 'a, c, b', then the number of correctly placed elements is 1.",
            "If correctness is not 100%, explain the correct matches. Otherwise, just briefly congratulate the student.",
            "If needed, a suggestion for how to better approach this kind of activity in the future, or a general suggestion for how to approach the study of similar topics. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.ORDERING: (
            "assess if the audience achieved ",
            f"To help you evaluate the answer, the correct order is '{solutions}'.",
            "The number of correctly placed elements in the list. For example, if the correct order is 'a, b, c', and the answer is 'a, c, b', then the number of correctly placed elements is 1.",
            "If correctness is not 100%, explain the correct order. Otherwise, just briefly congratulate the student.",
            "If needed, a suggestion for how to better approach this kind of activity in the future, or a general suggestion for how to approach the study of similar topics. Otherwise, just write 'not needed'.",
        ),

        # FILL_IN_THE_BLANKS
        TypeOfActivity.FILL_IN_THE_BLANKS: (
            "assess if the audience achieved ",
            f"To help you evaluate the answer, the correct order of the words is '{solutions}'.",
            "The number of correctly placed elements in the list. For example, if the correct order is 'a, b, c', and the answer is 'a, c, b', then the number of correctly placed elements is 1.",
            "If correctness is not 100%, explain which placements were incorrect and why. Otherwise, just briefly congratulate the student.",
            "If needed, a suggestion for how to better approach this kind of activity in the future, or a general suggestion for how to approach the study of similar topics. Otherwise, just write 'not needed'.",
        ),

        # QUESTION
        TypeOfActivity.TRUE_OR_FALSE: (
            "assess if the audience achieved ",
            f"To help you evaluate the answer, the correct answer is '{solutions[0]}'.",
            "A percentage between 0 and 100 that represents the correctness of the answer.",
            "If correctness is not 100%, explain the reasoning behind the given percentage, why the answer was not correct, and any other relevant information. Otherwise, just briefly congratulate the student.",
            "If needed, a suggestion for how to better approach this kind of activity in the future, or a general suggestion for how to approach the study of similar topics. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.SHORT_ANSWER_QUESTION: (
            "assess if the audience achieved ",
            f"To help you evaluate the answer, the correct answer is '{solutions[0]}'.",
            "A percentage between 0 and 100 that represents the correctness of the answer.",
            "If correctness is not 100%, explain the reasoning behind the given percentage, what was wrong and why. Otherwise, just briefly congratulate the student.",
            "If needed, a suggestion for how to better detect the exact words that should be used to answer short answer questions. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.OPEN_QUESTION: (
            "assess if the audience achieved ",
            f"To help you evaluate the answer, this is the list of key concepts that should be included in the answer: {solutions[0]}.",
            "A percentage between 0 and 100 that represents the correctness of the answer.",
            "If correctness is not 100%, explain the reasoning behind the given percentage, what was right, what was wrong, and any other relevant information. Otherwise, just briefly congratulate the student.",
            "If needed, a suggestion for how to better approach open questions for similar topics. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.CODING: (
            "assess if the audience achieved ",
            f"To help you evaluate the code, this is the list of requirements about what the code should do: {solutions}.",
            "A percentage between 0 and 100 that represents the correctness of the code.",
            "If correctness is not 100%, explain the reasoning behind the given percentage, what was wrong and why. Otherwise, just briefly congratulate the student.",
            "If needed, a suggestion for how to better approach open questions for similar topics. Otherwise, just write 'not needed'.",
        ),

        # THEORETICAL
        TypeOfActivity.ESSAY: (
            "assess if the audience achieved ",
            f"To help you evaluate the essay, this is the list of key concepts that should be included in the essay: {solutions}.",
            "A percentage between 0 and 100 that represents how well the essay adresses the assignment.",
            "Explain the reasoning behind the given percentage, what was appreciated, what could have been done better, and any other relevant information.",
            "If needed, a suggestion for how to better approach essays for similar topics. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.KNOWLEDGE_EXPOSITION: (
            "assess if the audience achieved ",
            f"To help you evaluate the exposition, this is the list of key concepts that should be included in the exposition: {solutions}.",
            "A percentage between 0 and 100 that represents how well the essay adresses the assignment.",
            "Explain the reasoning behind the given percentage, what was appreciated, what could have been done better, and any other relevant information.",
            "If needed, a suggestion for how to better approach expositions for similar topics. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.DEBATE: (
            "help the audience achieve ",
            f"To help you evaluate the results of the dabate, this is a list of possible key arguments and counterarguments related to the topic: {solutions}.",
            "The number of the winning group.",
            "Explain the reasoning behind the choice of the winning group, clearly say, for each group, which arguments were more convincing and why. Also, explain which arguments were not as convincing and why.",
            "If needed, a general suggestion for how to better approach debates in the future. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.BRAINSTORMING: (
            "help the audience achieve ",
            f"To help you evaluate the effectiveness of the brainstorming, here is a list of hints and/or questions provided to help the brainstorming: {solutions}.",
            "A percentage between 0 and 100 that represents the effectiveness of the brainstorming.",
            "Explain the reasoning behind the percentage, clearly say the most intriguing ideas and why, and explain which ideas were not as interesting and why.",
            "If needed, a general suggestion for how to better approach brainstormings in the future. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.GROUP_DISCUSSION: (
            "help the audience achieve ",
            "",
            "A percentage between 0 and 100 that represents the usefulness of the discussion.",
            "Explain the reasoning behind the percentage, clearly say the most intriguing points and why, and explain which points were not as interesting and why.",
            "If needed, a general suggestion for how to better approach group discussions in the future. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.SIMULATION: (
            "help the audience achieve ",
            "",
            "A percentage between 0 and 100 that represents the usefulness of the simulation.",
            "Explain which were the best interpreted chatacters and why, and explain which characters were not as well interpreted and why.",
            "If needed, a general suggestion for how to better approach simulations in the future. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.INQUIRY_BASED_LEARNING: (
            "help the audience achieve ",
            f"To help you evaluate the effectiveness of the inquiry-based learning, here is a list of potential areas of investigation or resources provided to guide the inquiry: {solutions}.",
            "A percentage between 0 and 100 that represents the effectiveness of the activity.",
            "Explain which were the best questions/discoveries and why, and explain which ones were not as good and why.",
            "If needed, a general suggestion for how to better approach inquiries in the future. Otherwise, just write 'not needed'.",
        ),

        # PRACTICAL
        TypeOfActivity.NON_WRITTEN_MATERIAL_ANALYSIS: (
            "assess if the audience achieved ",
            f"To help you evaluate the analysis, this is a list of the most important interpretations or features to identify: {solutions}.",
            "A percentage between 0 and 100 that represents the effectiveness of the activity.",
            "Explain which were the best discoveries and why, and explain which ones were not as good and why.",
            "If needed, a general suggestion for how to better approach analyses in the future. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.NON_WRITTEN_MATERIAL_PRODUCTION: (
            "assess if the audience achieved ",
            f"To help you evaluate the production, this is a list of the most important key elements or features that the produced material should include: {solutions}.",
            "A percentage between 0 and 100 that represents how well the produced material adresses the assignment.",
            "Explain the reasoning behind the given percentage, what was appreciated, what could have been done better, and any other relevant information.",
            "If needed, a suggestion for how to better approach productions for similar topics. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.CASE_STUDY_ANALYSIS: (
            "help the audience achieve ",
            f"To help you evaluate the analysis, here is a list of major problems or factors provided to guide the analysis: {solutions}.",
            "A percentage between 0 and 100 that represents the effectiveness of the activity.",
            "Explain which were the best discoveries and why, and explain which ones were not as good and why.",
            "If needed, a general suggestion for how to better approach analyses in the future. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.PROJECT_BASED_LEARNING: (
            "help the audience achieve ",
            f"To help you evaluate the project-based learning, here is a list of key stages or milestones to consider the project successful and complete: {solutions}.",
            "A percentage between 0 and 100 that represents how well the final project adresses the assignment.",
            "Explain the reasoning behind the given percentage, what was appreciated, what could have been done better, and any other relevant information.",
            "If needed, a suggestion for how to better approach similar projects in the future. Otherwise, just write 'not needed'.",
        ),
        TypeOfActivity.PROBLEM_SOLVING_ACTIVITY: (
            "assess if the audience achieved ",
            f"To help you evaluate the problem-solving activity, here is a list of possible and effective solutions provided to help the problem-solving activity: {solutions}.",
            "A percentage between 0 and 100 that represents how well the problem was solved.",
            "Explain the reasoning behind the given percentage, what insights were interesting, what could have been done better, and any other relevant information.",
            "If needed, a suggestion for how to better approach similar problems in the future. Otherwise, just write 'not needed'.",
        ),
    }
    activity_info = mapping.get(activity_type)
    if activity_info:
        return ActivityUtils(
            goal=activity_info[0],
            solution=activity_info[1],
            correctness=activity_info[2],
            comment=activity_info[3],
            advice=activity_info[4],
        )
    return None

"""Test text:
{
  "macro_subject": "History",
  "topic": "The Fall of the Western Roman Empire",
  "education_level": "high school",
  "learning_outcome": "the ability to recall or recognize simple facts and definitions",
  "assignment": "Descrivi almeno tre cause principali che portarono alla caduta dell'Impero Romano d'Occidente. Per ciascuna causa, fornisci un breve esempio o dettaglio che ne illustri l'impatto.",
  "answer": "Il declino dell'Impero Romano d'Occidente è stato causato da un insieme di fattori tra cui le invasioni barbariche, come il sacco di Roma da parte dei Visigoti nel 410 d.C., l’instabilità politica e la corruzione, evidenti nei frequenti cambi di imperatori e nelle guerre civili, il declino economico dovuto a inflazione, eccessiva tassazione e calo dei commerci, l’indebolimento dell’esercito con difficoltà di reclutamento e crescente uso di mercenari, e infine la divisione dell’Impero tra Occidente e Oriente, che ne ha minato l’unità e la forza.",
  "solutions": [
    "Invasioni barbariche (es. sacco di Roma da parte dei Visigoti nel 410 d.C.)",
    "Instabilità politica e corruzione (es. frequenti cambi di imperatori, guerre civili)",
    "Declino economico (es. inflazione, eccessiva tassazione, diminuzione del commercio)",
    "Esercito indebolito (es. difficoltà nel reclutamento, crescente dipendenza da mercenari)",
    "Divisione dell'Impero (es. divisione tra Impero Romano d'Occidente e d'Oriente)"
  ],
  "type": "open question",
  "language": "Itali",
  "model": "gemini"
}
"""

