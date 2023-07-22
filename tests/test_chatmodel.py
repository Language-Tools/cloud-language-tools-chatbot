import os
import sys
import logging
import unittest
import pytest
import json
import pprint
import audio_utils
from asgiref.sync import async_to_sync

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cloudlanguagetools
import cloudlanguagetools.servicemanager
import cloudlanguagetools.chatapi
import cloudlanguagetools_chatbot.chatmodel

logger = logging.getLogger(__name__)

def get_manager():
    manager = cloudlanguagetools.servicemanager.ServiceManager()
    manager.configure_default()
    return manager

class TestChatModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.manager = get_manager()

    def setUp(self):
        self.message_list = []
        self.audio_list = [] # list of tempfile.NamedTemporaryFile
        self.status_list = []
        logger.info('creating chat model')
        self.chat_model = cloudlanguagetools_chatbot.chatmodel.ChatModel(self.manager)
        self.chat_model.set_send_message_callback(self.send_message_fn, self.send_audio_fn, self.send_status_fn)
        self.process_message_sync = async_to_sync(self.chat_model.process_message)
        self.categorize_input_type_sync = async_to_sync(self.chat_model.categorize_input_type)

    async def send_status_fn(self, message):
        self.status_list.append(message)

    async def send_message_fn(self, message):
        self.message_list.append(message)
    
    async def send_audio_fn(self, audio_tempfile):
        self.audio_list.append(audio_tempfile)
    
    def verify_single_audio_message(self, expected_audio_message, recognition_language):
        self.assertEquals(len(self.audio_list), 1)  
        recognized_text = audio_utils.speech_to_text(self.manager, self.audio_list[0], recognition_language)
        self.assertEquals(audio_utils.sanitize_recognized_text(recognized_text), expected_audio_message)
        self.audio_list = []

    def verify_messages(self, expected_message_list):
        self.assertEquals(self.message_list, expected_message_list)
        self.message_list = []

    def test_french_translation(self):
        # pytest --log-cli-level=DEBUG tests/test_chatmodel.py -k test_french_translation

        self.process_message_sync("instructions: When given a sentence in French, translate it to English")

        self.process_message_sync("Je ne suis pas intéressé.")
        self.assertEquals(self.message_list, ["I'm not interested."])


    def test_chinese_translation_transliteration(self):
        # pytest --log-cli-level=DEBUG tests/test_chatmodel.py -k test_chinese_translation_transliteration

        self.process_message_sync("instructions: When given a sentence in Chinese, translate it to English, then transliterate the Chinese")

        self.process_message_sync("成本很低")
        self.assertEquals(self.message_list, ["The cost is low.", 'chéngběn hěn dī'])


    def test_chinese_translation_breakdown(self):
        # pytest --log-cli-level=DEBUG tests/test_chatmodel.py -k test_chinese_translation_breakdown

        instruction = "instructions: When given a sentence in Chinese, translate it to English, then breakdown the chinese sentence"
        self.process_message_sync(instruction)

        self.process_message_sync("成本很低")
        self.assertEquals(self.message_list, ["The cost is low.", """成本: chéngběn, (manufacturing, production etc) costs
很: hěn, very much
低: dī, lower (one's head)"""])


    def test_chinese_translation_audio(self):
        # pytest --log-cli-level=DEBUG tests/test_chatmodel.py -k test_chinese_translation_audio

        instruction = "your instructions: When given a sentence in Chinese, translate it to English, and pronounce the chinese sentence."
        self.process_message_sync(instruction)

        self.process_message_sync("成本很低")
        self.assertEquals(self.message_list, ["The cost is low"])

        # sometimes we get 2 sound files, that's OK
        # self.assertEquals(len(self.audio_list), 1)  
        recognized_text = audio_utils.speech_to_text(self.manager, self.audio_list[0], 'zh-CN')
        self.assertEquals(audio_utils.sanitize_recognized_text(recognized_text), '成本很低')

    def test_cantonese_audio(self):
        # pytest --log-cli-level=DEBUG tests/test_chatmodel.py -k test_cantonese_audio
        # pytest --log-cli-level=INFO tests/test_chatmodel.py -k test_cantonese_audio

        self.process_message_sync('pronounce "天氣預報" in cantonese')
        self.verify_single_audio_message('天氣預報', 'zh-HK')


    def test_cantonese_instructions(self):
        """test whether the model can follow steps repeatedly when given new input sentences"""
        instructions = 'instructions: when I give you a sentence in cantonese, pronounce it using Azure service, then translate it into english, and break down the cantonese sentence into words'
        self.process_message_sync(instructions)

        # first input sentence
        self.process_message_sync('呢條路係行返屋企嘅路')
        self.verify_single_audio_message('呢條路係行返屋企嘅路', 'zh-HK')
        self.verify_messages(['This road is the way home',
"""呢: nèi, this
條路: tìulou, road
係: hai, Oh, yes
行返: hàngfáan, Walk back
屋企: ūkkéi, home
嘅: gê, target
路: lou, road"""])

        # second input sentence
        self.process_message_sync('我最頂唔順嗰樣嘢')
        self.verify_single_audio_message('我最頂唔順果樣嘢', 'zh-HK')
        self.verify_messages(["I can't stand that kind of stuff the most",
"""我: ngǒ, I
最頂: zêoidíng, Top
唔: m, No
順: seon, shun
嗰: gó, that
樣: joeng, shape
嘢: jě, stuff"""])

        # third input sentence
        self.process_message_sync('黑社會')
        self.verify_single_audio_message('黑社會', 'zh-HK')
        self.verify_messages(["criminal underworld",
            """黑社會: hāksěwúi, underworld"""])        

    def test_cantonese_additional_questions_1(self):
        # pytest --log-cli-level=INFO tests/test_chatmodel.py -k test_cantonese_additional_questions

        """follow instructions, but then ask an additional question regarding a sentence"""
        instructions = 'instructions: when I give you a sentence in cantonese, pronounce it using Azure service, then translate it into english, and break down the cantonese sentence into words'
        self.process_message_sync(instructions)

        # send input sentence
        self.process_message_sync('黑社會')
        self.verify_single_audio_message('黑社會', 'zh-HK')
        self.verify_messages(["criminal underworld",
            """黑社會: hāksěwúi, underworld"""])        

        self.process_message_sync('when do we use this ?')
        # we should have an explanation from chatgpt
        self.assertEquals(len(self.message_list), 1)
        # make sure the word crime exists in the explanation
        self.assertIn('crim', self.message_list[0])

    def test_cantonese_additional_questions_2(self):
        # pytest --log-cli-level=INFO tests/test_chatmodel.py -k test_cantonese_additional_questions_2

        """follow instructions, but then ask an additional question regarding a sentence"""
        instructions = 'instructions: when I give you a sentence in cantonese, pronounce it using Azure service, then translate it into english, and break down the cantonese sentence into words'
        self.process_message_sync(instructions)

        # first input sentence
        self.process_message_sync('呢條路係行返屋企嘅路')
        self.verify_single_audio_message('呢條路係行返屋企嘅路', 'zh-HK')
        self.verify_messages(['This road is the way home',
"""呢: nèi, this
條路: tìulou, road
係: hai, Oh, yes
行返: hàngfáan, Walk back
屋企: ūkkéi, home
嘅: gê, target
路: lou, road"""])

        self.process_message_sync('Is there another chinese character which means road?')
        # we should have an explanation from chatgpt
        self.assertEquals(len(self.message_list), 1)
        self.assertIn('路', self.message_list[0])

    def test_cantonese_additional_questions_3(self):
        # pytest --log-cli-level=INFO tests/test_chatmodel.py -k test_cantonese_additional_questions_3
        # pytest --log-cli-level=DEBUG tests/test_chatmodel.py -k test_cantonese_additional_questions_3

        """follow instructions, but then ask an additional question regarding a sentence"""
        instructions = 'instructions: when I give you a sentence in cantonese, pronounce it using Azure service, then translate it into english, and break down the cantonese sentence into words'
        self.process_message_sync(instructions)

        # send input sentence
        self.process_message_sync('黑社會')
        self.verify_single_audio_message('黑社會', 'zh-HK')
        self.verify_messages(["criminal underworld",
            """黑社會: hāksěwúi, underworld"""])        

        self.process_message_sync('pronounce using amazon service')
        # print
        self.verify_single_audio_message('黑社會', 'zh-HK')

    def test_categorize_input(self):
        # pytest --log-cli-level=INFO tests/test_chatmodel.py -k test_categorize_input
        # pytest --log-cli-level=DEBUG tests/test_chatmodel.py -k test_categorize_input
        from cloudlanguagetools_chatbot.chatmodel import InputType

        self.assertEquals(self.categorize_input_type_sync('呢條路係行返屋企嘅路', 
                                                   'Is there another chinese character which means road?').input_type,
                                                   InputType.question_or_command)

        self.assertEquals(self.categorize_input_type_sync('呢條路係行返屋企嘅路', 
                                                   '黑社會').input_type,
                                                   InputType.new_sentence)

        self.assertEquals(self.categorize_input_type_sync('黑社會', 
                                                   'When do we use this ?').input_type,
                                                   InputType.question_or_command)

        self.assertEquals(self.categorize_input_type_sync('黑社會', 
                                                   'pronounce using amazon').input_type,
                                                   InputType.question_or_command)

        self.assertEquals(self.categorize_input_type_sync('黑社會', 
        'instructions: when I give you a sentence in cantonese, pronounce it using Azure service and female voice, then translate it into english, and break down the cantonese sentence into words').input_type,
                                                   InputType.instructions)

        self.assertEquals(self.categorize_input_type_sync('黑社會', 
        'instruction: translate from french to english').input_type,
                                                   InputType.instructions)

        self.assertEquals(self.categorize_input_type_sync(None, 
        '成绩').input_type,
                                                   InputType.new_sentence) 


    def test_mandarin_pinyin_1(self):
        # pytest --log-cli-level=INFO tests/test_chatmodel.py -k test_mandarin_pinyin_1

        # set instructions
        self.chat_model.set_instruction('I will send you some sentences in Chinese, follow my commands')

        # send input sentence
        self.process_message_sync('成绩')
        self.process_message_sync('pinyin')

        logger.debug(f'message_list: {self.message_list}')
        self.assertEquals(len(self.message_list), 2)
        self.assertEquals(self.message_list[1], 'chéngjì')


    def test_cantonese_jyutping_1(self):
        # pytest --log-cli-level=INFO tests/test_chatmodel.py -k test_cantonese_jyutping_1

        # set instructions
        self.chat_model.set_instruction('I will send you some sentences in Cantonese, follow my commands')

        # send input sentence
        self.process_message_sync('山路')
        self.process_message_sync('jyutping')

        logger.debug(f'message_list: {self.message_list}')
        self.assertEquals(len(self.message_list), 2)
        self.assertEquals(self.message_list[1], 'sāanlou')