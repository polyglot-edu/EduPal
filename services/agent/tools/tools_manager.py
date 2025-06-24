def get_tools() -> str:
    """
    Loads tool descriptions
    """
    get_oer_tool_description = """"""
    define_syllabus_tool_description = """
[
  {
    "name": "define_syllabus",
    "description": "Defines a syllabus for an educational course, it's meant to be used for long courses spanning over weeks or months",
    "parameters": {
      "type": "object",
      "properties": {
        "general_subject": {
          "type": "string",
          "description": "The general broad subject of the syllabus. (for example, "History of the Roman Empire", "The geography of Europe", etc.)"
        },
        "education_level": {
          "type": "string",
          "description": "The education level of the target audience."
          "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "additional_information": {
          "type": "string",
          "description": "Additional information about the syllabus. (for example specific sub-topics that should be included, specific learning outcomes, etc.)"
        },
        "language": {
          "type": "string",
          "description": "The language of the syllabus, defaults to \"English\"."
        },
        "model": {
          "type": "string",
          "description": "The model to use for generating the syllabus, defaults to \"Gemini\"."
        }
      },
      "required": ["general_subject", "education_level", "additional_information", "language", "model"],
    }
  },
"""
    plan_course_tool_description = """{
    "name": "plan_course",
    "description": "Plan an educational course based on a syllabus",
    "parameters": {
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
          "description": "The education level of the target audience."
          "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "learning_objectives": {
          "type": "object",
          "description": "the learning objectives of the lesson:"
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
        },
        "model": {
          "type": "string",
          "description": "the model to be used for the course, defualts to Gemini"
        }
      },
      "required": ["title", "macro_subject", "education_level", "learning_objectives", "number_of_lessons", "duration_of_lesson", "language", "model"]
    }
  },
  """
    plan_lesson_tool_description = """{
    "name": "plan_lesson",
    "description": "Plan an educational lesson that contains both learning activities and excercises about a topic",
    "parameters": {
      "type": "object",
      "properties": {
        "topics": {
          "type": "array",
          "description": "a list of topics to be covered in the lesson."
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
          "description": "the learning outcome of the activity"
          "enum": ["the ability to recall or recognize simple facts and definitions", "the ability to explain concepts and principles, and recognize how different ideas are related", "the ability to apply knowledge and perform operations in practical contexts", "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps", "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction", "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"]
        },
        "language": {
          "type": "string",
          "description": "the language of the lesson, defaults to \"English\""
        },
        "macro_subject": {
          "type": "string",
          "description": "the macro subject of the lesson"
        },
        "title": {
          "type": "string",
          "description": "the title of the lesson"
        },
        "education_level": {
          "type": "string",
          "description": "The education level of the target audience."
          "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "context": {
          "type": "string",
          "description": "the audience context, it is used to tailor the suggestions for the learning activity to the specific audience"
        },
        "model": {
          "type": "string",
          "description": "the model to be used for the lesson, defaults to Gemini"
        }
      },
      "required": ["topics", "learning_outcome", "language", "macro_subject", "title", "education_level", "context", "model"]
    }
"""
    generate_material_tool_description = """{
    "name": "generate_material",
    "description": "Generate educational material for a given topic, it's meant to be used inside a single lesson or ",
    "parameters": {
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
                "enum": ["the ability to recall or recognize simple facts and definitions", "the ability to explain concepts and principles, and recognize how different ideas are related", "the ability to apply knowledge and perform operations in practical contexts", "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps", "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction", "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"]
              },
              "topics": {
                "type": "array",
                "description": "A list of topics covered in the lesson node.",
                "items": {
                  "type": "object",
                  "properties": {
                    "topic": {
                      "type": "string",
                      "description": "the spacific topic"
                    },
                    "explanation": {
                      "type": "string",
                      "description": "the explanation of the topic and how it should be presented to the audience"
                    }
                  }
                }
              }
            }
          }
        },
        "education_level": {
          "type": "string",
          "description": "The education level of the target audience."
          "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "learning_outcome": {
          "type": "string",
          "description": "the learning outcome of the activity"
          "enum": ["the ability to recall or recognize simple facts and definitions", "the ability to explain concepts and principles, and recognize how different ideas are related", "the ability to apply knowledge and perform operations in practical contexts", "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps", "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction", "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"]
        },
        "duration": {
          "type": "integer",
          "description": "the duration of the material"
        },
        "language": {
          "type": "string",
          "description": "the language of the material, defaults to English"
        },
        "model": {
          "type": "string",
          "description": "the model to use, defaults to Gemini"
        }
      },
      "required": ["title", "macro_subject", "topics", "learning_outcome", "education_level", "duration", "language", "model"]
    }
  },
  """
    generate_activity_tool_description = """{
    "name": "generate_activity",
    "description": "Generate an educational activity, including both exercises and in-class activities",
    "parameters": {
      "type": "object",
      "properties": {
        "macro_subject": {
          "type": "string",
          "description": "the macro subject of the topic"
        },
        "topic": {
          "type": "string",
          "description": "the specific topic of the activity"
        },
        "education_level": {
          "type": "string",
          "description": "The education level of the target audience."
          "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "learning_outcome": {
          "type": "string",
          "description": "the learning outcome of the activity"
          "enum": ["the ability to recall or recognize simple facts and definitions", "the ability to explain concepts and principles, and recognize how different ideas are related", "the ability to apply knowledge and perform operations in practical contexts", "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps", "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction", "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"]
        },
        "material": {
          "type": "string",
          "description": "the material to ground on the generation of the activity"
        },
        "solutions_number": {
          "type": "integer",
          "description": "the number of solutions to generate"
        },
        "distractors_number": {
          "type": "integer",
          "description": "the number of distractors to generate. The distractors are answers similar to the correct answer, that are used to confuse the audience"
        },
        "easily_discardable_distractors_number": {
          "type": "integer",
          "description": "the number of easy distractors to generate. The easy distractors are completely wrong answers, that are easy to discard"
        },
        "type": {
          "type": "string",
          "description": "the type of the activity"
          "enum": ["open question", "short answer question", "true or false", "fill in the blanks", "matching", "ordering", "multiple choice", "multiple select", "coding", "essay", "knowledge exposition", "debate", "brainstorming", "group discussion", "simulation", "inquiry based learning", "non written material analysis", "non written material production", "case study analysis", "project based learning", "problem solving activity"]
        },
        "language": {
          "type": "string",
          "description": "the language of the activity, defaults to English"
        },
        "model": {
          "type": "string",
          "description": "the model to use, defaults to Gemini"
        }
      },
      "required": [ "macro_subject", "topic", "education_level", "learning_outcome", "material", "solutions_number", "distractors_number", "easily_discardable_distractors_number", "type", "language", "model" ]
    }
  },
  """
    evaluate_tool_description =  """{
    "name": "evaluate",
    "description": "Evaluate an educational activity",
    "parameters": {
    "type": "object",
    "properties": {
        "macro_subject": {
        "type": "string",
        "description": "the macro subject of the topic"
        },
        "topic": {
        "type": "string",
        "description": "the specific topic of the activity"
        },
        "education_level": {
        "type": "string",
        "description": "The education level of the target audience."
        "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "learning_outcome": {
        "type": "string",
        "description": "the learning outcome of the activity"
        "enum": ["the ability to recall or recognize simple facts and definitions", "the ability to explain concepts and principles, and recognize how different ideas are related", "the ability to apply knowledge and perform operations in practical contexts", "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps", "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction", "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"]
        },
        "assignment": {
        "type": "string",
        "description": "the assignment of the activity"
        },
        "answer": {
        "type": "string",
        "description": "the answer of the activity"
        },
        "solutions": {
        "type": "array",
        "description": "a list of the solutions of the activity",
        "items": {
            "type": "string"
        },
        },
        "type": {
        "type": "string",
        "description": "the type of the activity"
        "enum": ["open question", "short answer question", "true or false", "fill in the blanks", "matching", "ordering", "multiple choice", "multiple select", "coding", "essay", "knowledge exposition", "debate", "brainstorming", "group discussion", "simulation", "inquiry based learning", "non written material analysis", "non written material production", "case study analysis", "project based learning", "problem solving activity"]
        },
        "language": {
        "type": "string",
        "description": "the language of the activity, defaults to English"
        },
        "model": {
        "type": "string",
        "description": "the model to use, defaults to Gemini"
        }
    },
    "required": ["macro_subject", "topic", "education_level", "learning_outcome", "assignment", "answer", "solutions", "type", "language", "model"]
    }
  }
]"""
    
    return define_syllabus_tool_description + plan_course_tool_description + plan_lesson_tool_description + generate_material_tool_description + generate_activity_tool_description + evaluate_tool_description

def get_tools_short() -> str:
    return """
[
  {
    "name": "define_syllabus",
    "description": "Defines a syllabus for an educational course, it's meant to be used for long courses spanning over weeks or months"
  },
  {
    "name": "plan_course",
    "description": "Plan an educational course based on a syllabus"
  },
  {
    "name": "plan_lesson",
    "description": "Plan an educational lesson that contains both learning activities and exercises about a topic"
  },
  {
    "name": "generate_material",
    "description": "Generate educational material for a given topic, it's meant to be used inside a single lesson or"
  },
  {
    "name": "generate_activity",
    "description": "Generate an educational activity, including both exercises and in-class activities"
  },
  {
    "name": "evaluate",
    "description": "Evaluate an educational activity"
  }
]
"""

# example usage
if __name__ == "__main__":
    tools = get_tools()
    print(tools)

"""
[
  {
    "name": "define_syllabus",
    "description": "Defines a syllabus for an educational course",
    "parameters": {
      "type": "object",
      "properties": {
        "general_subject": {
          "type": "string",
          "description": "The general broad subject of the syllabus. (for example, "History of the Roman Empire", "The geography of Europe", etc.)"
        },
        "education_level": {
          "type": "string",
          "description": "The education level of the target audience."
          "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "additional_information": {
          "type": "string",
          "description": "Additional information about the syllabus. (for example specific sub-topics that should be included, specific learning outcomes, etc.)"
        },
        "language": {
          "type": "string",
          "description": "The language of the syllabus, defaults to "English"."
        },
        "model": {
          "type": "string",
          "description": "The model to use for generating the syllabus, defaults to "Gemini"."
        }
      },
      "required": ["general_subject", "education_level", "additional_information", "language", "model"],
    }
  },
{
    "name": "plan_course",
    "description": "Plan a course based on:",
    "parameters": {
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
          "description": "The education level of the target audience."
          "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "learning_objectives": {
          "type": "object",
          "description": "the learning objectives of the lesson:"
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
        },
        "model": {
          "type": "string",
          "description": "the model to be used for the course, defualts to Gemini"
        }
      },
      "required": ["title", "macro_subject", "education_level", "learning_objectives", "number_of_lessons", "duration_of_lesson", "language", "model"]
    }
  },
  {
    "name": "plan_lesson",
    "description": "Plan a lesson based on:",
    "parameters": {
      "type": "object",
      "properties": {
        "topics": {
          "type": "array",
          "description": "a list of topics to be covered in the lesson."
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
          "description": "the learning outcome of the activity"
          "enum": ["the ability to recall or recognize simple facts and definitions", "the ability to explain concepts and principles, and recognize how different ideas are related", "the ability to apply knowledge and perform operations in practical contexts", "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps", "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction", "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"]
        },
        "language": {
          "type": "string",
          "description": "the language of the lesson, defaults to "English""
        },
        "macro_subject": {
          "type": "string",
          "description": "the macro subject of the lesson"
        },
        "title": {
          "type": "string",
          "description": "the title of the lesson"
        },
        "education_level": {
          "type": "string",
          "description": "The education level of the target audience."
          "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "context": {
          "type": "string",
          "description": "the audience context, it is used to tailor the suggestions for the learning activity to the specific audience"
        },
        "model": {
          "type": "string",
          "description": "the model to be used for the lesson, defaults to Gemini"
        }
      },
      "required": ["topics", "learning_outcome", "language", "macro_subject", "title", "education_level", "context", "model"]
    }
{
    "name": "generate_material",
    "description": "Generate material for a given topic based on:",
    "parameters": {
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
                "enum": ["the ability to recall or recognize simple facts and definitions", "the ability to explain concepts and principles, and recognize how different ideas are related", "the ability to apply knowledge and perform operations in practical contexts", "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps", "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction", "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"]
              },
              "topics": {
                "type": "array",
                "description": "A list of topics covered in the lesson node.",
                "items": {
                  "type": "object",
                  "properties": {
                    "topic": {
                      "type": "string",
                      "description": "the spacific topic"
                    },
                    "explanation": {
                      "type": "string",
                      "description": "the explanation of the topic and how it should be presented to the audience"        
                    }
                  }
                }
              }
            }
          }
        },
        "education_level": {
          "type": "string",
          "description": "The education level of the target audience."
          "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "learning_outcome": {
          "type": "string",
          "description": "the learning outcome of the activity"
          "enum": ["the ability to recall or recognize simple facts and definitions", "the ability to explain concepts and principles, and recognize how different ideas are related", "the ability to apply knowledge and perform operations in practical contexts", "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps", "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction", "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"]
        },
        "duration": {
          "type": "integer",
          "description": "the duration of the material"
        },
        "language": {
          "type": "string",
          "description": "the language of the material, defaults to English"
        },
        "model": {
          "type": "string",
          "description": "the model to use, defaults to Gemini"
        }
      },
      "required": ["title", "macro_subject", "topics", "learning_outcome", "education_level", "duration", "language", "model"]
    }
  },
  {
    "name": "generate_activity",
    "description": "Generate an educational activity, including both exercises and in-class activities",
    "parameters": {
      "type": "object",
      "properties": {
        "macro_subject": {
          "type": "string",
          "description": "the macro subject of the topic"
        },
        "topic": {
          "type": "string",
          "description": "the specific topic of the activity"
        },
        "education_level": {
          "type": "string",
          "description": "The education level of the target audience."
          "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "learning_outcome": {
          "type": "string",
          "description": "the learning outcome of the activity"
          "enum": ["the ability to recall or recognize simple facts and definitions", "the ability to explain concepts and principles, and recognize how different ideas are related", "the ability to apply knowledge and perform operations in practical contexts", "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps", "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction", "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"]
        },
        "material": {
          "type": "string",
          "description": "the material to ground on the generation of the activity"
        },
        "solutions_number": {
          "type": "integer",
          "description": "the number of solutions to generate"
        },
        "distractors_number": {
          "type": "integer",
          "description": "the number of distractors to generate. The distractors are answers similar to the correct answer, that are used to confuse the audience"
        },
        "easily_discardable_distractors_number": {
          "type": "integer",
          "description": "the number of easy distractors to generate. The easy distractors are completely wrong answers, that are easy to discard"
        },
        "type": {
          "type": "string",
          "description": "the type of the activity"
          "enum": ["open question", "short answer question", "true or false", "fill in the blanks", "matching", "ordering", "multiple choice", "multiple select", "coding", "essay", "knowledge exposition", "debate", "brainstorming", "group discussion", "simulation", "inquiry based learning", "non written material analysis", "non written material production", "case study analysis", "project based learning", "problem solving activity"]
        },
        "language": {
          "type": "string",
          "description": "the language of the activity, defaults to English"
        },
        "model": {
          "type": "string",
          "description": "the model to use, defaults to Gemini"
        }
      },
      "required": [ "macro_subject", "topic", "education_level", "learning_outcome", "material", "solutions_number", "distractors_number", "easily_discardable_distractors_number", "type", "language", "model" ]
    }
  },
  {
    "name": "evaluate",
    "description": "Evaluate an educational activity",
    "parameters": {
    "type": "object",
    "properties": {
        "macro_subject": {
        "type": "string",
        "description": "the macro subject of the topic"
        },
        "topic": {
        "type": "string",
        "description": "the specific topic of the activity"
        },
        "education_level": {
        "type": "string",
        "description": "The education level of the target audience."
        "enum": ["elementary", "middle school", "high school", "college", "graduate", "professional"]
        },
        "learning_outcome": {
        "type": "string",
        "description": "the learning outcome of the activity"
        "enum": ["the ability to recall or recognize simple facts and definitions", "the ability to explain concepts and principles, and recognize how different ideas are related", "the ability to apply knowledge and perform operations in practical contexts", "the ability to assess your own understanding, identify gaps in knowledge, and strategize ways to close those gaps", "the ability to synthesize and organize concepts into a framework that allows for advanced problem-solving and prediction", "the ability to generate new knowledge, challenge existing paradigms, and make significant contributions to the field"]
        },
        "assignment": {
        "type": "string",
        "description": "the assignment of the activity"
        },
        "answer": {
        "type": "string",
        "description": "the answer of the activity"
        },
        "solutions": {
        "type": "array",
        "description": "a list of the solutions of the activity",
        "items": {
            "type": "string"
        },
        },
        "type": {
        "type": "string",
        "description": "the type of the activity"
        "enum": ["open question", "short answer question", "true or false", "fill in the blanks", "matching", "ordering", "multiple choice", "multiple select", "coding", "essay", "knowledge exposition", "debate", "brainstorming", "group discussion", "simulation", "inquiry based learning", "non written material analysis", "non written material production", "case study analysis", "project based learning", "problem solving activity"]
        },
        "language": {
        "type": "string",
        "description": "the language of the activity, defaults to English"
        },
        "model": {
        "type": "string",
        "description": "the model to use, defaults to Gemini"
        }
    },
    "required": ["macro_subject", "topic", "education_level", "learning_outcome", "assignment", "answer", "solutions", "type", "language", "model"]
    }
  }
]"""
