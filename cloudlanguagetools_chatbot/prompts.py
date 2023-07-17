
SYSTEM_MSG_ASSISTANT = "You are a helpful assistant specialized in translation and language learning."

DESCRIPTION_FN_IS_NEW_QUESTION = "Determine whether the last user message is a new input sentence unrelated to the previous one, "\
"or a question regarding the meaning, grammar, vocabulary of the previous sentence, or an instruction "\
"to explain, translate, transliterate, pronounce, lookup or break down the previous sentence"

DESCRIPTION_FLD_IS_NEW_QUESTION = """NEW_SENTENCE if the last user message is a new input sentence unrelated to the previous one.
QUESTION_OR_INSTRUCTION if it is a question regarding the meaning, grammar, vocabulary of the previous sentence, or an instruction
to explain, translate, transliterate, pronounce, lookup or break down the previous sentence. Examples of this include:
- What does it mean ?
- Explain in more details
- Pronounce using Amazon service
- Lookup in dictionary
- Break down the sentence
"""