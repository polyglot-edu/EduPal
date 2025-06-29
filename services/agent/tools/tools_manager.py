import json
import os
import aiohttp
from dotenv import load_dotenv
from mcp.types import Tool, TextContent
FASTAPI_BASE_URL = "http://131.114.22.98:8000"

load_dotenv()
ACCESS_KEY = os.getenv("TOOLS_SECRET_KEY", "")
MODEL = "GEMINI"

define_syllabus_tool = Tool(
    name="define_syllabus",
    description="Defines a syllabus based on subject, education level, and additional information. Returns a structured syllabus with goals, topics, and prerequisites.",
    inputSchema={
        "type": "object",
        "properties": {
            "general_subject": {
                "type": "string",
                "description": "The general broad subject of the syllabus (e.g., 'History of the Roman Empire', 'The geography of Europe')"
            },
            "education_level": {
                "type": "string",
                "description": "The education level of the target audience",
                "enum": ["ELEMENTARY", "MIDDLE_SCHOOL", "HIGH_SCHOOL", "COLLEGE", "GRADUATE", "PROFESSIONAL"]
            },
            "additional_information": {
                "type": "string",
                "description": "Additional information about the syllabus (specific sub-topics, learning outcomes, etc.)"
            },
            "language": {
                "type": "string",
                "description": "The language of the syllabus",
                "default": "English"
            }
        },
        "required": ["general_subject", "education_level", "additional_information", "language"]
    }
)

plan_course_tool = Tool(
    name="plan_course",
    description="Plan an educational course based on a syllabus",
    inputSchema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "the title of the course that will be generated"
            },
            "macro_subject": {
                "type": "string",
                "description": "the macro subject of the course"
            },
            "education_level": {
                "type": "string",
                "description": "The education level of the target audience.",
                "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
            },
            "learning_objectives": {
                "type": "object",
                "description": "This must be a JSON object with **exactly three string fields**: 'knowledge', 'skills', and 'attitude'. Do NOT use a list.",
                "properties": {
                    "knowledge": {
                        "type": "string",
                        "description": "the knowledge that the learner should acquire during the course"
                    },
                    "skills": {
                        "type": "string",
                        "description": "The skills that the learner should have at the end of the course."
                    },
                    "attitude": {
                        "type": "string",
                        "description": "The attitude that the learner should develop during the course."
                    }
                },
                "required": ["knowledge", "skills", "attitude"]
            },
            "number_of_lessons": {
                "type": "integer",
                "description": "the number of lessons in the course"
            },
            "duration_of_lesson": {
                "type": "integer",
                "description": "the duration (in minutes) of each lesson"
            },
            "language": {
                "type": "string",
                "description": "the language of the course, defaults to English"
            }
      },
        "required": ["title", "macro_subject", "education_level", "learning_objectives", "number_of_lessons", "duration_of_lesson", "language"]
    },
)

plan_lesson_tool = Tool(
    name="plan_lesson",
    description="Plan an educational lesson that contains both learning activities and excercises about a topic",
    inputSchema={
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "description": "a list of topics to be covered in the lesson.",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "the topic of the lesson"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "a brief explanation of the topic and how it should be covered in the lesson"
                        }
                    }
                }
            },
            "learning_outcome": {
                "type": "string",
                "enum": [
                  "DECLARATIVE",
                  "UNDERSTANDING", 
                  "PROCEDURAL",
                  "METACOGNITIVE",
                  "SCHEMATIC",
                  "TRANSFORMATIVE"
                ],
                "description": "The type of learning outcome",
                "enumDescriptions": [
                  "the ability to recall or recognize simple facts and definitions",
                  "the ability to explain concepts and principles, and recognize how different ideas are related", 
                  "the ability to apply knowledge and perform operations in practical contexts",
                  "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps",
                  "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction",
                  "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"
                ]
            },
            "language": {
                "type": "string",
                "description": "the language of the lesson, defaults to English"
            },
            "macro_subject": {
                "type": "string",
                "description": "the macro subject of the lesson (for example, 'Mathematics', 'Science', etc.)"
            },
            "title": {
                "type": "string",
                "description": "the title of the lesson"
            },
            "education_level": {
                "type": "string",
                "description": "The education level of the target audience",
                "enum": ["ELEMENTARY", "MIDDLE_SCHOOL", "HIGH_SCHOOL", "COLLEGE", "GRADUATE", "PROFESSIONAL"]
            },
            "context": {
                "type": "string",
                "description": "the audience context, it is used to tailor the suggestions for the learning activity to the specific audience"
            }
        },
        "required": ["topics", "learning_outcome", "language", "macro_subject", "title", "education_level", "context"]
    },
)

generate_material_tool = Tool(
    name="generate_material",
    description="Generate educational material for a given topic, it's meant to be used inside a single lesson or ",
    inputSchema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "the title of the material that will be generated"
            },
            "macro_subject": {
                "type": "string",
                "description": "the macro subject of the material"
            },
            "topics": {
                "type": "array",
                "description": "A list of lesson nodes.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the lesson node."
                        },
                        "learning_outcome": {
                            "type": "string",
                            "description": "the learning outcome of the activity"
                        },
                        "description": {
                            "type": "string",
                            "description": "a description of the activity"
                        },
                        "type": {
                            "type": "string",
                            "description": "the type of the activity"
                        }
                    }
                }
            },
            "education_level": {
                "type": "string",
                "description": "The education level of the target audience",
                "enum": ["ELEMENTARY", "MIDDLE_SCHOOL", "HIGH_SCHOOL", "COLLEGE", "GRADUATE", "PROFESSIONAL"]
            },
            "learning_outcome": {
                "type": "string",
                "enum": [
                  "DECLARATIVE",
                  "UNDERSTANDING", 
                  "PROCEDURAL",
                  "METACOGNITIVE",
                  "SCHEMATIC",
                  "TRANSFORMATIVE"
                ],
                "description": "The type of learning outcome",
                "enumDescriptions": [
                  "the ability to recall or recognize simple facts and definitions",
                  "the ability to explain concepts and principles, and recognize how different ideas are related", 
                  "the ability to apply knowledge and perform operations in practical contexts",
                  "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps",
                  "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction",
                  "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"
                ]
            },
            "duration": {
                "type": "integer",
                "description": "the time in minutes needed to complete the material"
            },
            "language": {
                "type": "string",
                "description": "the language of the lesson, defaults to English"
            }
        },
        "required": ["title", "macro_subject", "topics", "learning_outcome", "education_level", "duration", "language"]
    },
)

generate_activity_tool = Tool(
    name="generate_activity",
    description="Generate an educational activity, this tool can generate both exercises and in-class activities of more than 20 types",
    inputSchema={
        "type": "object",
        "properties": {
            "macro_subject": {
                "type": "string",
                "description": "the macro subject of the topic"
            },
            "topic": {
                "type": "string",
                "description": "title for the specific topic of the activity"
            },
            "topic_explanation": {
                "type": "string",
                "description": "very breif explanation of the topic"
            },
            "education_level": {
                "type": "string",
                "description": "The education level of the target audience",
                "enum": ["ELEMENTARY", "MIDDLE_SCHOOL", "HIGH_SCHOOL", "COLLEGE", "GRADUATE", "PROFESSIONAL"]
            },
            "learning_outcome": {
                "type": "string",
                "enum": [
                  "DECLARATIVE",
                  "UNDERSTANDING", 
                  "PROCEDURAL",
                  "METACOGNITIVE",
                  "SCHEMATIC",
                  "TRANSFORMATIVE"
                ],
                "description": "The type of learning outcome",
                "enumDescriptions": [
                  "the ability to recall or recognize simple facts and definitions",
                  "the ability to explain concepts and principles, and recognize how different ideas are related", 
                  "the ability to apply knowledge and perform operations in practical contexts",
                  "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps",
                  "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction",
                  "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"
                ]
            },
            "material": {
                "type": "string",
                "description": "the material with the ground truth and the information that will be used in the activity"
            },
            "solutions_number": {
                "type": "integer",
                "description": "the number of solutions/correct answers for the activity"
            },
            "distractors_number": {
                "type": "integer",
                "description": "the number of distractors/incorrect solutions for the activity"
            },
            "easily_discardable_distractors_number": {
                "type": "integer",
                "description": "the number of distractors that can be easily discarded for the activity"
            },
            "type": {
                "type": "string",
                "description": "The type of educational activity to create",
                "enum": [
                    "OPEN_QUESTION",
                    "SHORT_ANSWER_QUESTION", 
                    "TRUE_OR_FALSE",
                    "FILL_IN_THE_BLANKS",
                    "MATCHING",
                    "ORDERING",
                    "MULTIPLE_CHOICE",
                    "MULTIPLE_SELECT",
                    "CODING",
                    "ESSAY",
                    "KNOWLEDGE_EXPOSITION",
                    "DEBATE",
                    "BRAINSTORMING",
                    "GROUP_DISCUSSION",
                    "SIMULATION",
                    "INQUIRY_BASED_LEARNING",
                    "NON_WRITTEN_MATERIAL_ANALYSIS",
                    "NON_WRITTEN_MATERIAL_PRODUCTION",
                    "CASE_STUDY_ANALYSIS",
                    "PROJECT_BASED_LEARNING",
                    "PROBLEM_SOLVING_ACTIVITY"
                ]
            },
            "language": {
                "type": "string",
                "description": "the language of the activity, defaults to English"
            }
        },
        "required": ["macro_subject", "topic", "topic_explanation", "education_level", "learning_outcome", "material", "solutions_number", "distractors_number", "easily_discardable_distractors_number", "type", "language"]
    },
)

evaluate_activity_tool = Tool(
    name="evaluate_activity",
    description="Evaluate the quality of an educational activity, including both exercises and in-class activities",
    inputSchema={
        "type": "object",
        "properties": {
            "macro_subject": {
                "type": "string",
                "description": "the macro subject of the topic"
            },
            "topic": {
                "type": "string",
                "description": "title for the specific topic of the activity"
            },
            "education_level": {
                "type": "string",
                "description": "The education level of the target audience",
                "enum": ["ELEMENTARY", "MIDDLE_SCHOOL", "HIGH_SCHOOL", "COLLEGE", "GRADUATE", "PROFESSIONAL"]
            },
            "learning_outcome": {
                "type": "string",
                "enum": [
                  "DECLARATIVE",
                  "UNDERSTANDING", 
                  "PROCEDURAL",
                  "METACOGNITIVE",
                  "SCHEMATIC",
                  "TRANSFORMATIVE"
                ],
                "description": "The type of learning outcome",
                "enumDescriptions": [
                  "the ability to recall or recognize simple facts and definitions",
                  "the ability to explain concepts and principles, and recognize how different ideas are related", 
                  "the ability to apply knowledge and perform operations in practical contexts",
                  "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps",
                  "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction",
                  "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"
                ]
            },
            "assignment": {
                "type": "string",
                "description": "the assignment to evaluate"
            },
            "answer": {
                "type": "string", 
                "description": "the student's answer/s to the assignment"
            },
            "solutions": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "the correct answers for the assignment"
            },
            "type": {
                "type": "string",
                "description": "The type of educational activity to create",
                "enum": [
                    "OPEN_QUESTION",
                    "SHORT_ANSWER_QUESTION", 
                    "TRUE_OR_FALSE",
                    "FILL_IN_THE_BLANKS",
                    "MATCHING",
                    "ORDERING",
                    "MULTIPLE_CHOICE",
                    "MULTIPLE_SELECT",
                    "CODING",
                    "ESSAY",
                    "KNOWLEDGE_EXPOSITION",
                    "DEBATE",
                    "BRAINSTORMING",
                    "GROUP_DISCUSSION",
                    "SIMULATION",
                    "INQUIRY_BASED_LEARNING",
                    "NON_WRITTEN_MATERIAL_ANALYSIS",
                    "NON_WRITTEN_MATERIAL_PRODUCTION",
                    "CASE_STUDY_ANALYSIS",
                    "PROJECT_BASED_LEARNING",
                    "PROBLEM_SOLVING_ACTIVITY"
                ]
            },
            "language": {
                "type": "string",
                "description": "the language of the activity, defaults to English"
            }
        },
        "required": ["macro_subject", "topic", "education_level", "learning_outcome", "assignment", "answer", "solutions", "type", "language"]
    },
)

refine_tool = Tool(
    name="refine",
    description="Refine a given json object based on some instructions",
    inputSchema={
        "type": "object",
        "properties": {
            "json_object": {
                "type": "string",
                "description": "the json object to refine in string format"
            },
            "instructions": {
                "type": "string",
                "description": "the instructions to refine the json object"
            },
            "language": {
                "type": "string",
                "description": "the language of the object, defaults to English"
            }
        },
        "required": ["json", "instructions", "language"]
    },  
)

get_oers_collections_tool = Tool(
    name="get_oers_collections",
    description="Get a list of the available collections (each collection corresponds to a macro subject) inside the Open Educational Resources database",
    inputSchema={
        "type": "object",
        "properties": {},
        "required": []
    },
)

filter_oers_tool = Tool(
    name="filter_oers",
    description="Filter the Open Educational Resources database to find OERs that match some criteria",
    inputSchema={
        "type": "object",
        "properties": {
            "collection_name": {
                "type": "string",
                "description": "the name of the collection to search in"
            },
            "title": {
                "type": "string",
                "description": "the exact title of the resource to look for"
            },
            "description": {
                "type": "string",
                "description": "a text string to run a vector-based semantic search. Returns resources semantically similar to the description"
            },
            "education_level": {
                "type": "string",
                "description": "The education level of the target audience",
                "enum": ["ELEMENTARY", "MIDDLE_SCHOOL", "HIGH_SCHOOL", "COLLEGE", "GRADUATE", "PROFESSIONAL"]
            }
        },
        "required": ["collection_name"]
    },
)

async def handle_define_syllabus(arguments: dict) -> list[TextContent]:
    """Handle the define_syllabus API call"""
    try:        
        # Prepare the request
        url = f"{FASTAPI_BASE_URL}/tasks/define_syllabus"
        headers = {
            "Content-Type": "application/json",
            "access-key": ACCESS_KEY
        }
        
        # Set defaults for optional parameters
        payload = {
            "general_subject": arguments["general_subject"],
            "education_level": arguments["education_level"],
            "additional_information": arguments["additional_information"],
            "language": arguments.get("language", "English"),
            "model": MODEL
        }
        
        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return [TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=2)}"
                    )]
                else:
                    error_text = await response.text()
                    return [TextContent(
                        type="text",
                        text=f"Error calling define_syllabus API (Status {response.status}): {error_text}"
                    )]
                    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error in define_syllabus: {str(e)}"
        )]

async def handle_plan_course(arguments: dict) -> list[TextContent]:
    """Handle the plan_course API call"""
    try:
        url = f"{FASTAPI_BASE_URL}/tasks/plan_course"
        headers = {
            "Content-Type": "application/json",
            "access-key": ACCESS_KEY
        }

        # Prepare the payload
        payload = {
            "title": arguments["title"],
            "macro_subject": arguments["macro_subject"],
            "education_level": arguments["education_level"],
            "learning_objectives": arguments["learning_objectives"],
            "number_of_lessons": arguments["number_of_lessons"],
            "duration_of_lesson": arguments["duration_of_lesson"],
            "language": arguments.get("language", "English"),
            "model": MODEL
        }

        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return [TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=2)}"
                    )]
                else:
                    error_text = await response.text()
                    return [TextContent(
                        type="text",
                        text=f"Error calling plan_course API (Status {response.status}): {error_text}"
                    )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error in plan_course: {str(e)}"
        )]

async def handle_plan_lesson(arguments: dict) -> list[TextContent]:
    """Handle the plan_lesson API call"""
    try:
        url = f"{FASTAPI_BASE_URL}/tasks/plan_lesson"
        headers = {
            "Content-Type": "application/json",
            "access-key": ACCESS_KEY
        }

        # Prepare the payload
        payload = {
            "topics": arguments["topics"],
            "learning_outcome": arguments["learning_outcome"],
            "language": arguments.get("language", "English"),
            "macro_subject": arguments["macro_subject"],
            "title": arguments["title"],
            "education_level": arguments["education_level"],
            "context": arguments["context"],
            "model": MODEL
        }

        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return [TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=2)}"
                    )]
                else:
                    error_text = await response.text()
                    return [TextContent(
                        type="text",
                        text=f"Error calling plan_lesson API (Status {response.status}): {error_text}"
                    )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error in plan_lesson: {str(e)}"
        )]

async def handle_generate_material(arguments: dict) -> list[TextContent]:
    """Handle the generate_material API call"""
    try:
        url = f"{FASTAPI_BASE_URL}/tasks/generate_material"
        headers = {
            "Content-Type": "application/json",
            "access-key": ACCESS_KEY
        }

        # Prepare the payload
        payload = {
            "title": arguments["title"],
            "macro_subject": arguments["macro_subject"],
            "topics": arguments["topics"],
            "learning_outcome": arguments["learning_outcome"],
            "education_level": arguments["education_level"],
            "duration": arguments["duration"],
            "language": arguments.get("language", "English"),
            "model": MODEL
        }

        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return [TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=2)}"
                    )]
                else:
                    error_text = await response.text()
                    return [TextContent(
                        type="text",
                        text=f"Error calling generate_material API (Status {response.status}): {error_text}"
                    )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error in generate_material: {str(e)}"
        )]

async def handle_generate_activity(arguments: dict) -> list[TextContent]:
    """Handle the generate_activity API call"""
    try:
        url = f"{FASTAPI_BASE_URL}/tasks/generate_activity"
        headers = {
            "Content-Type": "application/json",
            "access-key": ACCESS_KEY
        }

        # Prepare the payload
        payload = {
            "macro_subject": arguments["macro_subject"],
            "topic": arguments["topic"],
            "topic_explanation": arguments["topic_explanation"],
            "education_level": arguments["education_level"],
            "learning_outcome": arguments["learning_outcome"],
            "material": arguments["material"],
            "solutions_number": arguments["solutions_number"],
            "distractors_number": arguments["distractors_number"],
            "easily_discardable_distractors_number": arguments["easily_discardable_distractors_number"],
            "type": arguments["type"],
            "language": arguments.get("language", "English"),
            "model": MODEL
        }

        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return [TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=2)}"
                    )]
                else:
                    error_text = await response.text()
                    return [TextContent(
                        type="text",
                        text=f"Error calling generate_activity API (Status {response.status}): {error_text}"
                    )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error in generate_activity: {str(e)}"
        )]

async def handle_evaluate_activity(arguments: dict) -> list[TextContent]:
    """Handle the evaluate_activity API call"""
    try:
        url = f"{FASTAPI_BASE_URL}/tasks/evaluate"
        headers = {
            "Content-Type": "application/json",
            "access-key": ACCESS_KEY
        }

        # Prepare the payload
        payload = {
            "macro_subject": arguments["macro_subject"],
            "topic": arguments["topic"],
            "education_level": arguments["education_level"],
            "learning_outcome": arguments["learning_outcome"],
            "assignment": arguments["assignment"],
            "answer": arguments["answer"],
            "solutions": arguments["solutions"],
            "type": arguments["type"],
            "language": arguments.get("language", "English"),
            "model": MODEL
        }

        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return [TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=2)}"
                    )]
                else:
                    error_text = await response.text()
                    return [TextContent(
                        type="text",
                        text=f"Error calling evaluate_activity API (Status {response.status}): {error_text}"
                    )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error in evaluate_activity: {str(e)}"
        )]

async def handle_refine(arguments: dict) -> list[TextContent]:
    """Handle the refine API call"""
    try:
        url = f"{FASTAPI_BASE_URL}/tasks/refine"
        headers = {
            "Content-Type": "application/json",
            "access-key": ACCESS_KEY
        }

        # Prepare the payload
        payload = {
            "json_object": arguments.get("json_object"),
            "instructions": arguments.get("instructions"),
            "language": arguments.get("language", "English"),
            "model": MODEL
        }

        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return [TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=2)}"
                    )]
                else:
                    error_text = await response.text()
                    return [TextContent(
                        type="text",
                        text=f"Error calling refine API (Status {response.status}): {error_text}"
                    )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error in refine: {str(e)}"
        )]

async def handle_get_oers_collections(arguments: dict) -> list[TextContent]:
    """Handle the get_oers_collections API call"""
    try:
        url = f"{FASTAPI_BASE_URL}/oers/get-oers-collections"
        headers = {
            "Content-Type": "application/json",
            "access-key": ACCESS_KEY
        }

        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={}, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return [TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=2)}"
                    )]
                else:
                    error_text = await response.text()
                    return [TextContent(
                        type="text",
                        text=f"Error calling get_oers_collections API (Status {response.status}): {error_text}"
                    )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error in get_oers_collections: {str(e)}"
        )]

async def handle_filter_oers(arguments: dict) -> list[TextContent]:
    """Handle the filter_oers API call"""
    try:
        url = f"{FASTAPI_BASE_URL}/oers/get-oers"
        headers = {
            "Content-Type": "application/json",
            "access-key": ACCESS_KEY
        }

        # Prepare the payload with required and optional fields
        payload = {
            "collection_name": arguments["collection_name"],
            "title": arguments.get("title"),
            "description": arguments.get("description"),
            "education_level": arguments.get("education_level"),
            "model": MODEL
        }

        # Remove None values to keep the payload clean
        payload = {k: v for k, v in payload.items() if v is not None}

        # Make the API call
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return [TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=2)}"
                    )]
                else:
                    error_text = await response.text()
                    return [TextContent(
                        type="text",
                        text=f"Error calling filter_oers API (Status {response.status}): {error_text}"
                    )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error in filter_oers: {str(e)}"
        )]

