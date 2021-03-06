from ipdata import *
import unittest

class TestAPIMethods(unittest.TestCase):

    def test_param_less(self):
        ipdata = IPData('test')
        status_code = ipdata.lookup().get('status')
        self.assertEqual(status_code, 200)

    def test_param(self):
        ipdata = IPData('test')
        status_code = ipdata.lookup('8.8.8.8').get('status')
        self.assertEqual(status_code, 200)
    
    def test_select_field(self):
        ipdata = IPData('test')
        response = ipdata.lookup('8.8.8.8', select_field='ip')
        self.assertEqual(response, {'ip': '8.8.8.8', 'status': 200})

    def test_fields_param(self):
        ipdata = IPData('test')
        response = ipdata.lookup('8.8.8.8',fields=['ip'])
        self.assertEqual(response, {'ip': '8.8.8.8', 'status': 200})

#    def test_bulk_lookup(self):
#        ipdata = ipdata('paid-key-here')
#        response = ipdata.bulk_lookup(['8.8.8.8','1.1.1.1'],fields=['ip'])
#        self.assertEqual(response, {'response': [{'ip': '8.8.8.8'}, {'ip': '1.1.1.1'}], 'status': 200})

if __name__ == '__main__':
    unittest.main()
