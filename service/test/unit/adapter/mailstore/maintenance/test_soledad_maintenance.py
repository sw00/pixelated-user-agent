#
# Copyright (c) 2015 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.
from leap.soledad.common.document import SoledadDocument
from twisted.internet import defer

from twisted.trial import unittest
from mockito import mock, when, verify, never
from pixelated.adapter.mailstore.maintenance import SoledadMaintenance
from leap.keymanager.openpgp import OpenPGPKey

SOME_EMAIL_ADDRESS = 'foo@example.tld'
SOME_KEY_ID = '4914254E384E264C'


class TestSoledadMaintenance(unittest.TestCase):

    def test_repair_is_deferred(self):
        soledad = mock()
        when(soledad).get_all_docs().thenReturn(defer.succeed((1, [])))

        d = SoledadMaintenance(soledad).repair()

        self.assertIsInstance(d, defer.Deferred)

    @defer.inlineCallbacks
    def test_repair_delete_public_key_active_docs(self):
        soledad = mock()
        key = self._public_key(SOME_EMAIL_ADDRESS, SOME_KEY_ID)
        active_doc = SoledadDocument(doc_id='some_doc', json=key.get_active_json(SOME_EMAIL_ADDRESS))
        when(soledad).get_all_docs().thenReturn(defer.succeed((1, [active_doc])))

        yield SoledadMaintenance(soledad).repair()

        verify(soledad).delete_doc(active_doc)

    @defer.inlineCallbacks
    def test_repair_delete_public_key_docs(self):
        soledad = mock()
        key = self._public_key(SOME_EMAIL_ADDRESS, SOME_KEY_ID)
        active_doc = SoledadDocument(doc_id='some_doc', json=key.get_active_json(SOME_EMAIL_ADDRESS))
        key_doc = SoledadDocument(doc_id='some_doc', json=key.get_json())
        when(soledad).get_all_docs().thenReturn(defer.succeed((1, [key_doc, active_doc])))

        yield SoledadMaintenance(soledad).repair()

        verify(soledad).delete_doc(active_doc)
        verify(soledad).delete_doc(key_doc)

    @defer.inlineCallbacks
    def test_repair_keeps_active_and_key_doc_if_private_key_exists(self):
        soledad = mock()
        key = self._public_key(SOME_EMAIL_ADDRESS, SOME_KEY_ID)
        private_key = self._private_key(SOME_EMAIL_ADDRESS, SOME_KEY_ID)
        active_doc = SoledadDocument(doc_id='some_doc', json=key.get_active_json(SOME_EMAIL_ADDRESS))
        key_doc = SoledadDocument(doc_id='some_doc', json=key.get_json())
        private_key_doc = SoledadDocument(doc_id='some_doc', json=private_key.get_json())
        when(soledad).get_all_docs().thenReturn(defer.succeed((1, [key_doc, active_doc, private_key_doc])))

        yield SoledadMaintenance(soledad).repair()

        verify(soledad, never).delete_doc(key_doc)
        verify(soledad, never).delete_doc(active_doc)
        verify(soledad, never).delete_doc(private_key_doc)

    @defer.inlineCallbacks
    def test_repair_only_deletes_key_docs(self):
        soledad = mock()
        key = self._public_key(SOME_EMAIL_ADDRESS, SOME_KEY_ID)
        key_doc = SoledadDocument(doc_id='some_doc', json=key.get_active_json(SOME_EMAIL_ADDRESS))
        other_doc = SoledadDocument(doc_id='something', json='{}')
        when(soledad).get_all_docs().thenReturn(defer.succeed((1, [key_doc, other_doc])))

        yield SoledadMaintenance(soledad).repair()

        verify(soledad, never).delete_doc(other_doc)

    @defer.inlineCallbacks
    def test_repair_recreates_public_key_active_doc_if_necessary(self):
        soledad = mock()

        private_key = self._private_key(SOME_EMAIL_ADDRESS, SOME_KEY_ID)
        private_key_doc = SoledadDocument(doc_id='some_doc', json=private_key.get_json())
        when(soledad).get_all_docs().thenReturn(defer.succeed((1, [private_key_doc])))

        yield SoledadMaintenance(soledad).repair()

        verify(soledad).create_doc_from_json('{"key_id": "4914254E384E264C", "tags": ["keymanager-active"], "type": "OpenPGPKey-active", "private": false, "address": "foo@example.tld"}')

    def _public_key(self, address, keyid):
        return self._gpgkey(address, keyid, private=False)

    def _private_key(self, address, keyid):
        return self._gpgkey(address, keyid, private=True)

    def _gpgkey(self, address, keyid, private=False):
        return OpenPGPKey(address, key_id=keyid, private=private)
