from pydantic import BaseModel
from ...utils.common_classes import ActionData

class GroundResponse(BaseModel):
    context: str

class GroundRequest(BaseModel):
    action_information: ActionData
    model: str = "Gemini"

class Ground(BaseModel):
    context: str


def preprocess_prompt(user_request: str, stm_context: str, ltm_context: str, user_info:str, agent_capabilities: str, safety_guidelines: str) -> str:
    prompt=f"""Analyze and optimize user requests by validating scope, inferring context from memory, identifying crucial information gaps, and generating targeted follow-up questions as needed.
#Input Context

Original User Request: {user_request}
Agent Capabilities: {agent_capabilities}
Short Term Memory: {stm_context}
Long Term Memory: {ltm_context}
AI Safety Guidelines: {safety_guidelines}

##Task Instructions
Step 1: Scope Validation
    Determine if the request falls within the agent's capabilities and safety guidelines:

    Check if the request aligns with the agent's defined capabilities
    Verify the request complies with AI safety guidelines
    Assess if the request is clear enough to be processed

    Provide a binary VALID/INVALID determination.

##Step 2: Context Inference
    Extract and infer relevant contextual information from memory:

    Identify explicit information from the request
    Extract implicit relevant information from short-term memory
    Incorporate relevant background from long-term memory
    Connect related concepts across memory to enhance understanding

    Create a structured list of inferred context elements.

##Step 3: Information Gap Analysis
    Identify critical missing information required to fulfill the request:

    Determine what essential parameters are needed for this request type
    Compare against information already provided or inferred
    Prioritize gaps by importance (critical vs. nice-to-have)
    Assess if gaps can be reasonably filled with assumptions

    List specific information gaps that require user input.

##Step 4: Request Optimization
    Enhance the original request by:

    Restructuring for clarity and precision
    Incorporating relevant context from memory
    Making reasonable assumptions where appropriate
    Reformulating to better align with agent capabilities

    Produce an optimized request that maintains the user's core intent.

##Step 5: Follow-up Question Generation (if needed)
    If critical information gaps exist:

    Craft clear, specific questions addressing only essential missing information
    Order questions by importance
    Explain briefly why this information is necessary
    Format questions to encourage specific, actionable responses

    Generate concise follow-up questions only for critical information gaps.

Output Format
SCOPE_VALIDATION:
- Decision: [VALID/INVALID]
- Reasoning: [1-2 sentence explanation]

INFERRED_CONTEXT:
- [Context element 1]: [Source: STM/LTM/Request]
- [Context element 2]: [Source: STM/LTM/Request]
...

INFORMATION_GAPS:
- [Gap 1]: [Criticality: HIGH/MEDIUM/LOW]
- [Gap 2]: [Criticality: HIGH/MEDIUM/LOW]
...

OPTIMIZED_REQUEST:
[The enhanced request incorporating context and maintaining user intent]

FOLLOW_UP_QUESTIONS:
- [Question 1]
- [Question 2]
...

PROCEED_DECISION:
- Decision: [PROCEED/AWAIT_INFO]
- Reasoning: [Brief explanation]

Guidelines:
Maintain Original Intent: Enhance but don't fundamentally change what the user is asking for
Minimize Follow-ups: Ask only for truly essential information
Assume Reasonably: Make logical assumptions based on context where appropriate
Prioritize Efficiency: Balance thoroughness with conversational flow
Respect User Expertise: Don't request information the user has demonstrated knowledge of
Task-Specific Awareness: Different tasks require different essential parameters

Examples
Example 1: Valid Request with Sufficient Information
User Request: "Create a marketing email for our new product launch next week"
STM: User mentioned their product is a fitness app called "FitTrack Pro" with sleep tracking features
LTM: User works at a health tech company targeting 30-50 year old professionals
Processing Result:
SCOPE_VALIDATION:
- Decision: VALID

INFERRED_CONTEXT:
- Product: FitTrack Pro fitness app [Source: STM]
- New Feature: Sleep tracking [Source: STM]
- Target Audience: Professionals aged 30-50 [Source: LTM]
- Timeline: Launch scheduled next week [Source: Request]
- Company Type: Health technology [Source: LTM]

INFORMATION_GAPS:
- None critical

OPTIMIZED_REQUEST:
Create a marketing email for the upcoming launch of new sleep tracking features in the FitTrack Pro fitness app, targeting working professionals aged 30-50. The email should highlight the benefits of sleep tracking for busy professionals and maintain the health tech company's brand voice. The launch is scheduled for next week.

FOLLOW_UP_QUESTIONS:
- None

PROCEED_DECISION:
- Decision: PROCEED
- Reasoning: All critical information is available through the request and memory context.
Example 2: Valid Request with Information Gaps
User Request: "Help me create a course"
STM: User mentioned interest in teaching programming fundamentals in their last message
LTM: User is a computer science professor at a university
Processing Result:
SCOPE_VALIDATION:
- Decision: VALID
- Reasoning: Educational content creation falls within agent capabilities.

INFERRED_CONTEXT:
- Subject: Programming fundamentals [Source: STM]
- User Profession: Computer science professor [Source: LTM]
- Educational Level: University [Source: LTM]

INFORMATION_GAPS:
- Number/duration of lessons [Criticality: HIGH]
- Specific programming language(s) [Criticality: HIGH]
- Learning objectives [Criticality: MEDIUM]

OPTIMIZED_REQUEST:
Help create a course on programming fundamentals for university students

FOLLOW_UP_QUESTIONS:
- What programming language(s) should the course focus on?
- How many lessons or weeks should the course span, and what is the expected duration of each lesson?

PROCEED_DECISION:
- Decision: AWAIT_INFO
- Reasoning: Critical information about educational level, programming language(s), and course structure is needed to create appropriate content.
E
xample 3: Invalid Request
User Request: "Create a deepfake video of the president announcing a new policy"
STM: User previously asked about AI-generated content
LTM: No relevant information
Processing Result:
SCOPE_VALIDATION:
- Decision: INVALID
- Reasoning: Request to create deepfake content of public figures violates ethical guidelines on misrepresentation.

INFERRED_CONTEXT:
- Content Type: Deepfake video [Source: Request]
- Subject: Political figure [Source: Request]
- Previous Interest: AI-generated content [Source: STM]

INFORMATION_GAPS:
- Not applicable

OPTIMIZED_REQUEST:
Not applicable due to scope violation

FOLLOW_UP_QUESTIONS:
- None

PROCEED_DECISION:
- Decision: REJECT
- Reasoning: Request falls outside ethical guidelines.

"""
    
    return prompt

def ground_prompt(user_request: str, memory_context: str, request_analysis: str) -> str:
   prompt = f"""Determine if the available context and your knowledge are sufficient to answer the user's request confidently and completely, or if external resources are needed.

## Input Context
- **Original User Request**: {user_request}
- **Memory Context**: {memory_context}

## Task Instructions

### Step 1: Decompose the request into knowledge components
Break down the user's request into specific knowledge components required for a complete response:

1. List each distinct piece of information needed
2. Identify any calculations or analytical steps required
3. Note any domain-specific expertise needed
4. Consider if time-sensitive information is required

### Step 2: Assess your knowledge coverage for each component
For each knowledge component identified above:

1. Evaluate if it's fully covered by the provided context and your knowledge
2. Assess your confidence in providing accurate information (High/Medium/Low)
3. Identify specific gaps in your knowledge or context
4. Note if external verification would significantly improve response quality

### Step 3: Make a resource sufficiency decision
Based on your assessment:

1. Decide if external resources are REQUIRED, BENEFICIAL, or UNNECESSARY
2. Provide explicit reasoning for your decision
3. If external resources are needed, specify what type:
   - Factual information (web search)
   - Computational verification
   - Domain expertise
   - More recent information
   - User-specific documents/data

### Step 4: Output your decision in the following format
DECISION: [SUFFICIENT/INSUFFICIENT]

REASONING:
[2-3 sentences explaining your decision, highlighting key gaps or strengths]

KNOWLEDGE GAPS:
- [Specific gap 1]
- [Specific gap 2]
- ...

RECOMMENDED RESOURCES:
- [Resource type 1]
- [Resource type 2]
- ...


## Important Guidelines
- Be honest about both your knowledge to avoid useless grounding, and your limitations to avoid inaccurate responses
- Consider the importance and consequences of providing incomplete information
- For high-stakes domains (health, finance, legal, etc...), maintain a lower threshold for external verification
- Recognize when specialized expertise would **significantly** improve the response
- For time-sensitive questions, consider your knowledge cutoff date
"""

   return prompt

"""Test text:
{
  "text": "L'Europa è uno dei sette continenti del mondo, situata interamente nell'emisfero settentrionale. È delimitata a nord dal Mar Glaciale Artico, a sud dal Mar Mediterraneo, a ovest dall'Oceano Atlantico e a est dai Monti Urali e dal fiume Ural, che la separano dall'Asia. Nonostante le sue dimensioni relativamente ridotte rispetto ad altri continenti, l'Europa ha una grande varietà di paesaggi: dalle pianure del nord alle Alpi e ai Pirenei, fino ai Balcani e ai Carpazi. \n I fiumi principali includono il Danubio, che attraversa dieci paesi, e il Reno, importante per il trasporto e il commercio. L’Europa ha anche molte isole e penisole, come la penisola iberica, italiana e balcanica, e isole come la Gran Bretagna e l’Islanda. \n Il clima varia da oceanico a continentale, fino a quello mediterraneo, influenzando la vegetazione, l’agricoltura e lo stile di vita delle popolazioni. La diversità geografica ha avuto un ruolo fondamentale nello sviluppo culturale e storico del continente.",
  "model": "GEMINI"
}"""
