from ..common_enums import TextStyle, EducationLevel, LearningOutcome
from pydantic import BaseModel

class SummarizeResponse(BaseModel):
    summary: str
    keywords: list[str] = None

class SummarizeRequest(BaseModel):
    text: str
    model: str = "Gemini"
    style: TextStyle = TextStyle.STANDARD
    education_level: EducationLevel = EducationLevel.HIGH_SCHOOL
    learning_outcome: LearningOutcome = LearningOutcome.DECLARATIVE

def summarize_prompt(text, style=TextStyle.STANDARD, level=EducationLevel.HIGH_SCHOOL, learning_outcome=LearningOutcome.DECLARATIVE):
   prompt = f"""Summarize in a {style} style, and maintaining the same language of the text, the text: '{text}'.
List the ten keywords most relevant to the topic.
Summarize the text to make it understandable for a {level} audience that needs to achieve a {learning_outcome} learning outcome on the topic. If the text does not contain enough information to achieve the learning outcome, please integrate the necessary information from your own knowledge and expertiese."""
   return prompt

"""Test text:
Quantum computing is a type of computation that takes advantage of quantum mechanical phenomena, such as superposition and entanglement. It uses quantum bits (qubits) instead of classical bits to perform calculations. Quantum computers have the potential to solve certain problems much faster than classical computers, making them a promising technology for fields like cryptography, optimization, and drug discovery. However, they are still in the early stages of development and face significant technical challenges before they can be widely used.
A computação quântica é um tipo de computação que aproveita os fenômenos da mecânica quântica, como a superposição e o emaranhamento. Ela utiliza qubits, em vez de bits clássicos, para realizar cálculos. Os computadores quânticos têm o potencial de resolver certos problemas muito mais rapidamente do que os computadores clássicos, tornando-os uma tecnologia promissora para áreas como criptografia, otimização e descoberta de medicamentos. No entanto, ainda estão em estágios iniciais de desenvolvimento e enfrentam desafios técnicos significativos antes de poderem ser amplamente utilizados.
"""
