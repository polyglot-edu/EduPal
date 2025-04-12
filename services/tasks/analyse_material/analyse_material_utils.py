from ..common_enums import EducationLevel, LearningOutcome
from ..plan_lesson.plan_lesson_utils import Topic
from pydantic import BaseModel

class AnalyseMaterialResponse(BaseModel):
    language: str
    macro_subject: str
    title: str
    education_level: EducationLevel
    learning_outcome: LearningOutcome
    topics: list[Topic]
    keywords: list[str]
    prerequisites: list[str]
    estimated_duration: int

class AnalyseMaterialRequest(BaseModel):
    text: str
    model: str = "Gemini"

class Analysis(BaseModel):
    language: str
    macro_subject: str
    title: str
    education_level: EducationLevel
    learning_outcome: LearningOutcome
    topics: list[Topic]
    keywords: list[str]
    prerequisites: list[str]
    estimated_duration: int


def analyse_material_prompt(text):
   prompt = f"""You are an expert multilingual educator specialized in analysing educational material.

### Task
Your task is to analyse the following material to extract meaningful information that will helpcorrectly categorize it.
Material:
{text}

### Information Structure
Since you are highly organized, you will follow a structured approach to categorize the material. You will extract the following information:
- **Language** (in English): The language of the material.
- **Macro Subject** (in material's language): The general subject of the material. For example, if the material is about the the Roman Empire, the macro subject could be "History".
- **Title** (in material's language): A short title that summarizes the content of the material.
- **Education Level** (in English from the provided list): The educational level that the material is intended for.
- **Learning Outcome** (in English from the provided list): The specific learning outcome that the material aims to achieve.
- **Topics** (in material's language): A list of the main topics covered in the material. Each topic is composed by:
    - **Topic** (in material's language): The name of the topic.
    - **Explanation** (in material's language): A description of which parts of the topic are covered and how they are covered.
- **Keywords** (in material's language): A list of keywords that describe the material.
- **Prerequisites** (in material's language): A list of the prerequisites that the learner should have before starting the material.
- **Estimated Duration** (in minutes): The estimated time required to carefully read and understand the material.

Here are the available **Education Level** options:
{", ".join(e.value for e in EducationLevel)}

Here are the available **Learning Outcome** options:
{", ".join(e.value for e in LearningOutcome)}
"""
   return prompt

"""Test text:
{
  "text": "L'Europa è uno dei sette continenti del mondo, situata interamente nell'emisfero settentrionale. È delimitata a nord dal Mar Glaciale Artico, a sud dal Mar Mediterraneo, a ovest dall'Oceano Atlantico e a est dai Monti Urali e dal fiume Ural, che la separano dall'Asia. Nonostante le sue dimensioni relativamente ridotte rispetto ad altri continenti, l'Europa ha una grande varietà di paesaggi: dalle pianure del nord alle Alpi e ai Pirenei, fino ai Balcani e ai Carpazi. \n I fiumi principali includono il Danubio, che attraversa dieci paesi, e il Reno, importante per il trasporto e il commercio. L’Europa ha anche molte isole e penisole, come la penisola iberica, italiana e balcanica, e isole come la Gran Bretagna e l’Islanda. \n Il clima varia da oceanico a continentale, fino a quello mediterraneo, influenzando la vegetazione, l’agricoltura e lo stile di vita delle popolazioni. La diversità geografica ha avuto un ruolo fondamentale nello sviluppo culturale e storico del continente.",
  "model": "GEMINI"
}"""
