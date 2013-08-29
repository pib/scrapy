import unittest

from scrapy.contrib.loader import ItemLoader, XPathItemLoader
from scrapy.contrib.loader.processor import Join, Identity, TakeFirst, \
    Compose, MapCompose
from scrapy.item import Item, Field
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse


# test items
class NameItem(Item):
    name = Field()


class TestItem(NameItem):
    url = Field()
    summary = Field()


# test item loaders
class NameItemLoader(ItemLoader):
    default_item_class = TestItem


class TestItemLoader(NameItemLoader):
    name_in = MapCompose(lambda v: v.title())


class DefaultedItemLoader(NameItemLoader):
    default_input_processor = MapCompose(lambda v: v[:-1])


# test processors
def processor_with_args(value, other=None, loader_context=None):
    if 'key' in loader_context:
        return loader_context['key']
    return value


class ItemLoaderTest(unittest.TestCase):

    def test_load_item_using_default_loader(self):
        i = TestItem()
        i['summary'] = 'lala'
        il = ItemLoader(item=i)
        il.add_value('name', 'marta')
        item = il.load_item()
        assert item is i
        self.assertEqual(item['summary'], 'lala')
        self.assertEqual(item['name'], ['marta'])

    def test_load_item_using_custom_loader(self):
        il = TestItemLoader()
        il.add_value('name', 'marta')
        item = il.load_item()
        self.assertEqual(item['name'], ['Marta'])

    def test_add_value(self):
        il = TestItemLoader()
        il.add_value('name', 'marta')
        self.assertEqual(il.get_collected_values('name'), ['Marta'])
        self.assertEqual(il.get_output_value('name'), ['Marta'])
        il.add_value('name', 'pepe')
        self.assertEqual(il.get_collected_values('name'), ['Marta', 'Pepe'])
        self.assertEqual(il.get_output_value('name'), ['Marta', 'Pepe'])

        # test add object value
        il.add_value('summary', {'key': 1})
        self.assertEqual(il.get_collected_values('summary'), [{'key': 1}])

        il.add_value(None, 'Jim', lambda x: {'name': x})
        self.assertEqual(il.get_collected_values('name'), ['Marta', 'Pepe', 'Jim'])

    def test_add_zero(self):
        il = NameItemLoader()
        il.add_value('name', 0)
        self.assertEqual(il.get_collected_values('name'), [0])

    def test_replace_value(self):
        il = TestItemLoader()
        il.replace_value('name', 'marta')
        self.assertEqual(il.get_collected_values('name'), ['Marta'])
        self.assertEqual(il.get_output_value('name'), ['Marta'])
        il.replace_value('name', 'pepe')
        self.assertEqual(il.get_collected_values('name'), ['Pepe'])
        self.assertEqual(il.get_output_value('name'), ['Pepe'])

        il.replace_value(None, 'Jim', lambda x: {'name': x})
        self.assertEqual(il.get_collected_values('name'), ['Jim'])

    def test_get_value(self):
        il = NameItemLoader()
        self.assertEqual('FOO', il.get_value(['foo', 'bar'], TakeFirst(), str.upper))
        self.assertEqual(['foo', 'bar'], il.get_value(['name:foo', 'name:bar'], re='name:(.*)$'))
        self.assertEqual('foo', il.get_value(['name:foo', 'name:bar'], TakeFirst(), re='name:(.*)$'))

        il.add_value('name', ['name:foo', 'name:bar'], TakeFirst(), re='name:(.*)$')
        self.assertEqual(['foo'], il.get_collected_values('name'))
        il.replace_value('name', 'name:bar', re='name:(.*)$')
        self.assertEqual(['bar'], il.get_collected_values('name'))

    def test_iter_on_input_processor_input(self):
        class NameFirstItemLoader(NameItemLoader):
            name_in = TakeFirst()

        il = NameFirstItemLoader()
        il.add_value('name', 'marta')
        self.assertEqual(il.get_collected_values('name'), ['marta'])
        il = NameFirstItemLoader()
        il.add_value('name', ['marta', 'jose'])
        self.assertEqual(il.get_collected_values('name'), ['marta'])

        il = NameFirstItemLoader()
        il.replace_value('name', 'marta')
        self.assertEqual(il.get_collected_values('name'), ['marta'])
        il = NameFirstItemLoader()
        il.replace_value('name', ['marta', 'jose'])
        self.assertEqual(il.get_collected_values('name'), ['marta'])

        il = NameFirstItemLoader()
        il.add_value('name', 'marta')
        il.add_value('name', ['jose', 'pedro'])
        self.assertEqual(il.get_collected_values('name'), ['marta', 'jose'])

    def test_map_compose_filter(self):
        def filter_world(x):
            return None if x == 'world' else x

        proc = MapCompose(filter_world, str.upper)
        self.assertEqual(proc(['hello', 'world', 'this', 'is', 'scrapy']),
                         ['HELLO', 'THIS', 'IS', 'SCRAPY'])

    def test_map_compose_filter_multil(self):
        class TestItemLoader(NameItemLoader):
            name_in = MapCompose(lambda v: v.title(), lambda v: v[:-1])

        il = TestItemLoader()
        il.add_value('name', 'marta')
        self.assertEqual(il.get_output_value('name'), ['Mart'])
        item = il.load_item()
        self.assertEqual(item['name'], ['Mart'])

    def test_default_input_processor(self):
        il = DefaultedItemLoader()
        il.add_value('name', 'marta')
        self.assertEqual(il.get_output_value('name'), ['mart'])

    def test_inherited_default_input_processor(self):
        class InheritDefaultedItemLoader(DefaultedItemLoader):
            pass

        il = InheritDefaultedItemLoader()
        il.add_value('name', 'marta')
        self.assertEqual(il.get_output_value('name'), ['mart'])

    def test_input_processor_inheritance(self):
        class ChildItemLoader(TestItemLoader):
            url_in = MapCompose(lambda v: v.lower())

        il = ChildItemLoader()
        il.add_value('url', 'HTTP://scrapy.ORG')
        self.assertEqual(il.get_output_value('url'), ['http://scrapy.org'])
        il.add_value('name', 'marta')
        self.assertEqual(il.get_output_value('name'), ['Marta'])

        class ChildChildItemLoader(ChildItemLoader):
            url_in = MapCompose(lambda v: v.upper())
            summary_in = MapCompose(lambda v: v)

        il = ChildChildItemLoader()
        il.add_value('url', 'http://scrapy.org')
        self.assertEqual(il.get_output_value('url'), ['HTTP://SCRAPY.ORG'])
        il.add_value('name', 'marta')
        self.assertEqual(il.get_output_value('name'), ['Marta'])

    def test_empty_map_compose(self):
        class IdentityDefaultedItemLoader(DefaultedItemLoader):
            name_in = MapCompose()

        il = IdentityDefaultedItemLoader()
        il.add_value('name', 'marta')
        self.assertEqual(il.get_output_value('name'), ['marta'])

    def test_identity_input_processor(self):
        class IdentityDefaultedItemLoader(DefaultedItemLoader):
            name_in = Identity()

        il = IdentityDefaultedItemLoader()
        il.add_value('name', 'marta')
        self.assertEqual(il.get_output_value('name'), ['marta'])

    def test_extend_custom_input_processors(self):
        class ChildItemLoader(TestItemLoader):
            name_in = MapCompose(TestItemLoader.name_in, str.swapcase)

        il = ChildItemLoader()
        il.add_value('name', 'marta')
        self.assertEqual(il.get_output_value('name'), ['mARTA'])

    def test_extend_default_input_processors(self):
        class ChildDefaultedItemLoader(DefaultedItemLoader):
            name_in = MapCompose(DefaultedItemLoader.default_input_processor, str.swapcase)

        il = ChildDefaultedItemLoader()
        il.add_value('name', 'marta')
        self.assertEqual(il.get_output_value('name'), ['MART'])

    def test_output_processor_using_function(self):
        il = TestItemLoader()
        il.add_value('name', ['mar', 'ta'])
        self.assertEqual(il.get_output_value('name'), ['Mar', 'Ta'])

        class TakeFirstItemLoader(TestItemLoader):
            name_out = " ".join

        il = TakeFirstItemLoader()
        il.add_value('name', ['mar', 'ta'])
        self.assertEqual(il.get_output_value('name'), 'Mar Ta')

    def test_output_processor_error(self):
        class TestItemLoader(ItemLoader):
            default_item_class = TestItem
            name_out = MapCompose(float)

        il = TestItemLoader()
        il.add_value('name', ['$10'])
        try:
            float('$10')
        except Exception as e:
            expected_exc_str = str(e)

        exc = None
        try:
            il.load_item()
        except Exception as e:
            exc = e
        assert isinstance(exc, ValueError)
        s = str(exc)
        assert 'name' in s, s
        assert '$10' in s, s
        assert 'ValueError' in s, s
        assert expected_exc_str in s, s

    def test_output_processor_using_classes(self):
        il = TestItemLoader()
        il.add_value('name', ['mar', 'ta'])
        self.assertEqual(il.get_output_value('name'), ['Mar', 'Ta'])

        class TakeFirstItemLoader(TestItemLoader):
            name_out = Join()

        il = TakeFirstItemLoader()
        il.add_value('name', ['mar', 'ta'])
        self.assertEqual(il.get_output_value('name'), 'Mar Ta')

        class TakeFirstItemLoader(TestItemLoader):
            name_out = Join("<br>")

        il = TakeFirstItemLoader()
        il.add_value('name', ['mar', 'ta'])
        self.assertEqual(il.get_output_value('name'), 'Mar<br>Ta')

    def test_default_output_processor(self):
        il = TestItemLoader()
        il.add_value('name', ['mar', 'ta'])
        self.assertEqual(il.get_output_value('name'), ['Mar', 'Ta'])

        class LalaItemLoader(TestItemLoader):
            default_output_processor = Identity()

        il = LalaItemLoader()
        il.add_value('name', ['mar', 'ta'])
        self.assertEqual(il.get_output_value('name'), ['Mar', 'Ta'])

    def test_loader_context_on_declaration(self):
        class ChildItemLoader(TestItemLoader):
            url_in = MapCompose(processor_with_args, key='val')

        il = ChildItemLoader()
        il.add_value('url', 'text')
        self.assertEqual(il.get_output_value('url'), ['val'])
        il.replace_value('url', 'text2')
        self.assertEqual(il.get_output_value('url'), ['val'])

    def test_loader_context_on_instantiation(self):
        class ChildItemLoader(TestItemLoader):
            url_in = MapCompose(processor_with_args)

        il = ChildItemLoader(key='val')
        il.add_value('url', 'text')
        self.assertEqual(il.get_output_value('url'), ['val'])
        il.replace_value('url', 'text2')
        self.assertEqual(il.get_output_value('url'), ['val'])

    def test_loader_context_on_assign(self):
        class ChildItemLoader(TestItemLoader):
            url_in = MapCompose(processor_with_args)

        il = ChildItemLoader()
        il.context['key'] = 'val'
        il.add_value('url', 'text')
        self.assertEqual(il.get_output_value('url'), ['val'])
        il.replace_value('url', 'text2')
        self.assertEqual(il.get_output_value('url'), ['val'])

    def test_item_passed_to_input_processor_functions(self):
        def processor(value, loader_context):
            return loader_context['item']['name']

        class ChildItemLoader(TestItemLoader):
            url_in = MapCompose(processor)

        it = TestItem(name='marta')
        il = ChildItemLoader(item=it)
        il.add_value('url', 'text')
        self.assertEqual(il.get_output_value('url'), ['marta'])
        il.replace_value('url', 'text2')
        self.assertEqual(il.get_output_value('url'), ['marta'])

    def test_add_value_on_unknown_field(self):
        il = TestItemLoader()
        self.assertRaises(KeyError, il.add_value, 'wrong_field', ['lala', 'lolo'])

    def test_compose_processor(self):
        class TestItemLoader(NameItemLoader):
            name_out = Compose(lambda v: v[0], lambda v: v.title(), lambda v: v[:-1])

        il = TestItemLoader()
        il.add_value('name', ['marta', 'other'])
        self.assertEqual(il.get_output_value('name'), 'Mart')
        item = il.load_item()
        self.assertEqual(item['name'], 'Mart')


class ProcessorsTest(unittest.TestCase):

    def test_take_first(self):
        proc = TakeFirst()
        self.assertEqual(proc([None, '', 'hello', 'world']), 'hello')
        self.assertEqual(proc([None, '', 0, 'hello', 'world']), 0)

    def test_identity(self):
        proc = Identity()
        self.assertEqual(proc([None, '', 'hello', 'world']),
                         [None, '', 'hello', 'world'])

    def test_join(self):
        proc = Join()
        self.assertRaises(TypeError, proc, [None, '', 'hello', 'world'])
        self.assertEqual(proc(['', 'hello', 'world']), ' hello world')
        self.assertEqual(proc(['hello', 'world']), 'hello world')
        self.assert_(isinstance(proc(['hello', 'world']), str))

    def test_compose(self):
        proc = Compose(lambda v: v[0], str.upper)
        self.assertEqual(proc(['hello', 'world']), 'HELLO')
        proc = Compose(str.upper)
        self.assertEqual(proc(None), None)
        proc = Compose(str.upper, stop_on_none=False)
        self.assertRaises(TypeError, proc, None)

    def test_mapcompose(self):
        filter_world = lambda x: None if x == 'world' else x
        proc = MapCompose(filter_world, str.upper)
        self.assertEqual(proc(['hello', 'world', 'this', 'is', 'scrapy']),
                         ['HELLO', 'THIS', 'IS', 'SCRAPY'])


class TestXPathItemLoader(XPathItemLoader):
    default_item_class = TestItem
    name_in = MapCompose(lambda v: v.title())


class XPathItemLoaderTest(unittest.TestCase):
    response = HtmlResponse(url="", body='<html><body><div id="id">marta</div><p>paragraph</p></body></html>')

    def test_constructor_errors(self):
        self.assertRaises(RuntimeError, XPathItemLoader)

    def test_constructor_with_selector(self):
        sel = HtmlXPathSelector(text="<html><body><div>marta</div></body></html>")
        l = TestXPathItemLoader(selector=sel)
        self.assert_(l.selector is sel)
        l.add_xpath('name', '//div/text()')
        self.assertEqual(l.get_output_value('name'), ['Marta'])

    def test_constructor_with_response(self):
        l = TestXPathItemLoader(response=self.response)
        self.assert_(l.selector)
        l.add_xpath('name', '//div/text()')
        self.assertEqual(l.get_output_value('name'), ['Marta'])

    def test_add_xpath_re(self):
        l = TestXPathItemLoader(response=self.response)
        l.add_xpath('name', '//div/text()', re='ma')
        self.assertEqual(l.get_output_value('name'), ['Ma'])

    def test_replace_xpath(self):
        l = TestXPathItemLoader(response=self.response)
        self.assert_(l.selector)
        l.add_xpath('name', '//div/text()')
        self.assertEqual(l.get_output_value('name'), ['Marta'])
        l.replace_xpath('name', '//p/text()')
        self.assertEqual(l.get_output_value('name'), ['Paragraph'])

        l.replace_xpath('name', ['//p/text()', '//div/text()'])
        self.assertEqual(l.get_output_value('name'), ['Paragraph', 'Marta'])

    def test_get_xpath(self):
        l = TestXPathItemLoader(response=self.response)
        self.assertEqual(l.get_xpath('//p/text()'), ['paragraph'])
        self.assertEqual(l.get_xpath('//p/text()', TakeFirst()), 'paragraph')
        self.assertEqual(l.get_xpath('//p/text()', TakeFirst(), re='pa'), 'pa')

        self.assertEqual(l.get_xpath(['//p/text()', '//div/text()']), ['paragraph', 'marta'])

    def test_replace_xpath_multi_fields(self):
        l = TestXPathItemLoader(response=self.response)
        l.add_xpath(None, '//div/text()', TakeFirst(), lambda x: {'name': x})
        self.assertEqual(l.get_output_value('name'), ['Marta'])
        l.replace_xpath(None, '//p/text()', TakeFirst(), lambda x: {'name': x})
        self.assertEqual(l.get_output_value('name'), ['Paragraph'])

    def test_replace_xpath_re(self):
        l = TestXPathItemLoader(response=self.response)
        self.assert_(l.selector)
        l.add_xpath('name', '//div/text()')
        self.assertEqual(l.get_output_value('name'), ['Marta'])
        l.replace_xpath('name', '//div/text()', re='ma')
        self.assertEqual(l.get_output_value('name'), ['Ma'])


if __name__ == "__main__":
    unittest.main()
