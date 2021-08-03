import functools
import unittest

from input_pipeline import DataConfig
from metadata_processors import PROCESSORS, MetadataProcessor
from metadata_utils import chunks, create_global_metadata_prefix, add_metadata_and_chunk_examples, add_local_metadata_to_text

from datasets import Dataset
from transformers import GPT2TokenizerFast


class MetadataUtilsTester(unittest.TestCase):

    def setUp(self) -> None:
        self.tokenizer = GPT2TokenizerFast.from_pretrained("gpt2-xl")
        self.examples = [
            {"id": "0001",
             "text": "It was a brilliant first round. You have to break down the Cuban's rhythm you can't let them get into rhythm. The risk with that is Yafai has got to go him.",
             "metadata": [{"key": "url", "type": "global", "value": "https://www.bbc.com/sport/live/olympics/50974152"},
                          {"key": "timestamp", "type": "global", "value": "2018-12-10T13:45:00.000Z"},
                          {"key": "entity", "type": "local", "char_start_idx": 132, "char_end_idx": 137, "value": "Galal Yafai"}]},
            {"id": "0002",
             "text": "An apple is an edible fruit produced by an apple tree (Malus domestica).",
             "metadata": [{"key": "url", "type": "global", "value": "https://en.wikipedia.org/wiki/Apple"},
                          {"key": "html", "type": "local", "value": "b", "char_start_idx": 3, "char_end_idx": 8},
                          {"key": "entity", "type": "local", "value": "Malus domestica", "char_start_idx": 3, "char_end_idx": 8},
                          {"key": "html", "type": "local", "value": "b", "char_start_idx": 43, "char_end_idx": 53},
                          {"key": "html", "type": "local", "value": "i", "char_start_idx": 43, "char_end_idx": 48}]}
        ]

    def test_chunks(self):
        list1 = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
        list2 = [0, 1, 2, 3, 4, 5, 6]
        self.assertEqual(list([x for x, *_ in chunks(1, list1)]), [['a'], ['b'], ['c'], ['d'], ['e'], ['f'], ['g']])
        self.assertEqual(list([x for x, *_ in chunks(len(list1), list1)]), [list1])
        self.assertEqual(list([x for x, *_ in chunks(3, list1)]), [['a', 'b', 'c'], ['d', 'e', 'f'], ['g']])
        self.assertEqual(list([x for x, *_ in chunks(3, list1)]), [['a', 'b', 'c'], ['d', 'e', 'f'], ['g']])
        self.assertEqual(list([x for x, _ in chunks(3, list1, list2)]), [['a', 'b', 'c'], ['d', 'e', 'f'], ['g']])
        self.assertEqual(list([x for _, x in chunks(3, list1, list2)]), [[0, 1, 2], [3, 4, 5], [6]])

    def test_create_global_metadata_prefix(self):
        cfg = DataConfig()
        cfg.metadata_key_value_sep = ": "
        cfg.metadata_sep = " | "
        cfg.global_metadata_sep = " |||"
        cfg.metadata_list = ["url", "timestamp"]
        PROCESSORS["url"] = MetadataProcessor
        PROCESSORS["timestamp"] = MetadataProcessor

        self.assertEqual(create_global_metadata_prefix(self.examples[0], cfg),
                         "url: https://www.bbc.com/sport/live/olympics/50974152 | timestamp: 2018-12-10T13:45:00.000Z |||")
        self.assertEqual(create_global_metadata_prefix(self.examples[1], cfg), "url: https://en.wikipedia.org/wiki/Apple |||")

    def test_add_local_metadata_to_text(self):
        cfg = DataConfig()
        cfg.metadata_list = ["html", "entity"]
        PROCESSORS["html"] = MetadataProcessor
        PROCESSORS["entity"] = MetadataProcessor
        text1, mask1 = add_local_metadata_to_text(self.examples[0], cfg)
        text2, mask2 = add_local_metadata_to_text(self.examples[1], cfg)

        self.assertEqual(text1,
                         "It was a brilliant first round. You have to break down the Cuban's rhythm you can't let them get into rhythm. The risk with that is [entity: Galal Yafai]Yafai[/entity: Galal Yafai] has got to go him.")
        self.assertEqual(''.join(str(int(x)) for x in mask1),
                         "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001111111111111111111110000011111111111111111111110000000000000000000")

        self.assertEqual(text2,
                         "An [entity: Malus domestica][html: b]apple[/html: b][/entity: Malus domestica] is an edible fruit produced by an [html: b][html: i]apple[/html: i] tree[/html: b] (Malus domestica).")
        self.assertEqual(''.join(str(int(x)) for x in mask2),
                         "000111111111111111111111111111111111100000111111111111111111111111111111111111000000000000000000000000000000000001111111111111111110000011111111110000011111111110000000000000000000")

    def test_add_metadata_and_chunk_examples(self):
        cfg = DataConfig()
        cfg.metadata_list = ["url", "timestamp", "html", "entity"]
        cfg.max_seq_len = 64

        ds_dict = {key: [self.examples[0][key], self.examples[1][key]] for key in self.examples[0].keys()}
        ds = Dataset.from_dict(ds_dict)

        mapped_ds = ds.map(functools.partial(add_metadata_and_chunk_examples, tokenizer=self.tokenizer, cfg=cfg), batched=True,
                           remove_columns=ds.column_names, load_from_cache_file=False)

        self.assertEqual(self.tokenizer.convert_ids_to_tokens(mapped_ds[0]['input_ids']),
                         ['url', ':', 'Ġhttps', '://', 'www', '.', 'bb', 'c', '.', 'com', '/', 's', 'port', '/', 'live', '/', 'oly', 'mp',
                          'ics', '/', '509', '74', '152', 'Ġ|', 'Ġtimestamp', ':', 'Ġ2018', '-', '12', '-', '10', 'T', '13', ':', '45', ':',
                          '00', '.', '000', 'Z', 'Ġ||', '|', 'ĠIt', 'Ġwas', 'Ġa', 'Ġbrilliant', 'Ġfirst', 'Ġround', '.', 'ĠYou', 'Ġhave',
                          'Ġto', 'Ġbreak', 'Ġdown', 'Ġthe', 'ĠCuban', "'s", 'Ġrhythm', 'Ġyou', 'Ġcan', "'t", 'Ġlet', 'Ġthem', 'Ġget'])
        self.assertEqual(mapped_ds[0]['attention_mask'],
                         [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(mapped_ds[0]['metadata_mask'],
                         [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

        self.assertEqual(self.tokenizer.convert_ids_to_tokens(mapped_ds[1]['input_ids']),
                         ['url', ':', 'Ġhttps', '://', 'www', '.', 'bb', 'c', '.', 'com', '/', 's', 'port', '/', 'live', '/', 'oly', 'mp',
                          'ics', '/', '509', '74', '152', 'Ġ|', 'Ġtimestamp', ':', 'Ġ2018', '-', '12', '-', '10', 'T', '13', ':', '45', ':',
                          '00', '.', '000', 'Z', 'Ġ||', '|', 'Ġinto', 'Ġrhythm', '.', 'ĠThe', 'Ġrisk', 'Ġwith', 'Ġthat', 'Ġis', 'Ġ[',
                          'entity', ':', 'ĠGal', 'al', 'ĠY', 'af', 'ai', ']', 'Y', 'af', 'ai', '[/', 'entity'])
        self.assertEqual(mapped_ds[1]['attention_mask'],
                         [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(mapped_ds[1]['metadata_mask'],
                         [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1])

        self.assertEqual(self.tokenizer.convert_ids_to_tokens(mapped_ds[2]['input_ids']),
                         ['url', ':', 'Ġhttps', '://', 'www', '.', 'bb', 'c', '.', 'com', '/', 's', 'port', '/', 'live', '/', 'oly', 'mp',
                          'ics', '/', '509', '74', '152', 'Ġ|', 'Ġtimestamp', ':', 'Ġ2018', '-', '12', '-', '10', 'T', '13', ':', '45', ':',
                          '00', '.', '000', 'Z', 'Ġ||', '|', ':', 'ĠGal', 'al', 'ĠY', 'af', 'ai', ']', 'Ġhas', 'Ġgot', 'Ġto', 'Ġgo', 'Ġhim',
                          '.', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>',
                          '<|endoftext|>', '<|endoftext|>', '<|endoftext|>'])
        self.assertEqual(mapped_ds[2]['attention_mask'],
                         [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(mapped_ds[2]['metadata_mask'],
                         [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

        self.assertEqual(self.tokenizer.convert_ids_to_tokens(mapped_ds[3]['input_ids']),
                         ['url', ':', 'Ġhttps', '://', 'en', '.', 'wikipedia', '.', 'org', '/', 'wiki', '/', 'Apple', 'Ġ||', '|', 'ĠAn',
                          'Ġ[', 'entity', ':', 'ĠMal', 'us', 'Ġdomest', 'ica', '][', 'html', ':', 'Ġb', ']', 'apple', '[/', 'html', ':',
                          'Ġb', '][/', 'entity', ':', 'ĠMal', 'us', 'Ġdomest', 'ica', ']', 'Ġis', 'Ġan', 'Ġedible', 'Ġfruit', 'Ġproduced',
                          'Ġby', 'Ġan', 'Ġ[', 'html', ':', 'Ġb', '][', 'html', ':', 'Ġi', ']', 'apple', '[/', 'html', ':', 'Ġi', ']',
                          'Ġtree'])
        self.assertEqual(mapped_ds[3]['attention_mask'],
                         [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(mapped_ds[3]['metadata_mask'],
                         [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                          1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0])

        self.assertEqual(self.tokenizer.convert_ids_to_tokens(mapped_ds[4]['input_ids']),
                         ['url', ':', 'Ġhttps', '://', 'en', '.', 'wikipedia', '.', 'org', '/', 'wiki', '/', 'Apple', 'Ġ||', '|', '[/',
                          'html', ':', 'Ġb', ']', 'Ġ(', 'Mal', 'us', 'Ġdomest', 'ica', ').', '<|endoftext|>', '<|endoftext|>',
                          '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>',
                          '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>',
                          '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>',
                          '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>',
                          '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>',
                          '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>', '<|endoftext|>'])
        self.assertEqual(mapped_ds[4]['attention_mask'],
                         [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                          0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(mapped_ds[4]['metadata_mask'],
                         [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                          0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])


if __name__ == '__main__':
    unittest.main()
