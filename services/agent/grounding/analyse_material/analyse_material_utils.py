from pydantic import BaseModel
from ...tools.plan_lesson.plan_lesson_utils import Topic
from ...utils.common_enums import EducationLevel, LearningOutcome

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
    model: str = "default"

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
   prompt = f"""You are an expert educator specialized in analysing educational material.

### Task
Your task is to analyse the following material to extract meaningful information that will help correctly categorize it.
Material:
{text}

### Information Structure
Since you are highly organized, you will follow a structured approach to categorize the material. You will extract the following information:
- **Language** (in English): The main language the material is in. Note that material could have some words in other languages, but the main language is the one that is used for most of the content.
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

def analyse_image_prompt():
   prompt = f"""You are an educational AI specialized in analyzing and explaining images in detail.

Given the following image, perform a deep analysis and describe it thoroughly.

Your description must include:

A clear and structured description of the visual elements (objects, people, animals, places, colors, textures, actions, etc.).

Relevant historical, cultural, scientific, or technical facts connected to what is visible in the image.

Interesting trivia or lesser-known educational facts that would help a student learn more about the subject of the image.

Explanation of potential educational value (e.g., what could be taught using this image in subjects like history, biology, art, geography, technology, etc.).

Use technical, engaging, and informative language.
The output should be structured into these sections:

1. Visual Description:
[Detailed description of what's in the image]

2. Related Educational Facts:
[Facts linked to objects, animals, people, or places in the image — historical, scientific, cultural, etc.]

3. Trivia & Fun Facts:
[Any surprising or interesting pieces of knowledge that add educational value]

4. Suggested Educational Uses:
[Suggestions on how this image could be integrated in lessons]

Start the analysis now.
"""
   return prompt


"""Test text:
{
  "text": "L'Europa è uno dei sette continenti del mondo, situata interamente nell'emisfero settentrionale. È delimitata a nord dal Mar Glaciale Artico, a sud dal Mar Mediterraneo, a ovest dall'Oceano Atlantico e a est dai Monti Urali e dal fiume Ural, che la separano dall'Asia. Nonostante le sue dimensioni relativamente ridotte rispetto ad altri continenti, l'Europa ha una grande varietà di paesaggi: dalle pianure del nord alle Alpi e ai Pirenei, fino ai Balcani e ai Carpazi. \n I fiumi principali includono il Danubio, che attraversa dieci paesi, e il Reno, importante per il trasporto e il commercio. L’Europa ha anche molte isole e penisole, come la penisola iberica, italiana e balcanica, e isole come la Gran Bretagna e l’Islanda. \n Il clima varia da oceanico a continentale, fino a quello mediterraneo, influenzando la vegetazione, l’agricoltura e lo stile di vita delle popolazioni. La diversità geografica ha avuto un ruolo fondamentale nello sviluppo culturale e storico del continente.",
  "model": "GEMINI"
}"""
