from pydantic import BaseModel

class TranslateResponse(BaseModel):
    translation: str

class TranslateRequest(BaseModel):
    text: str
    language: str = "English"
    model: str = "Gemini"

def translate_prompt(text, language="English"):
   prompt = f"""Translate the following text into {language}: '{text}'.
   If the text is a JSON, translate only the values an return the same JSON with translated values.
   In every case, return only the translation, without any additional text or explanation."""
   return prompt

"""Test inputs:
Quantum computing is a type of computation that takes advantage of quantum mechanical phenomena, such as superposition and entanglement. It uses quantum bits (qubits) instead of classical bits to perform calculations. Quantum computers have the potential to solve certain problems much faster than classical computers, making them a promising technology for fields like cryptography, optimization, and drug discovery. However, they are still in the early stages of development and face significant technical challenges before they can be widely used.
A computação quântica é um tipo de computação que aproveita os fenômenos da mecânica quântica, como a superposição e o emaranhamento. Ela utiliza qubits, em vez de bits clássicos, para realizar cálculos. Os computadores quânticos têm o potencial de resolver certos problemas muito mais rapidamente do que os computadores clássicos, tornando-os uma tecnologia promissora para áreas como criptografia, otimização e descoberta de medicamentos. No entanto, ainda estão em estágios iniciais de desenvolvimento e enfrentam desafios técnicos significativos antes de poderem ser amplamente utilizados.
"""
