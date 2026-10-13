"""One observation cycle with synthetic frames; never touches a game window."""
from collections import deque
from pathlib import Path
import threading
import unittest
from unittest.mock import Mock,patch
import numpy as np

from currency_war_assistant.controller import Controller
from currency_war_assistant.models import GameState,Seen
from currency_war_assistant.vision import StateTracker


class OwnedChangeTests(unittest.TestCase):
    def test_owned_change_never_starts_public_list_refresh(self):
        c=object.__new__(Controller)
        c.closing=False;c.running=True;c._wake=Mock();c._mutex=threading.RLock()
        c.data=Path('tests/_cache/absent');c.tracker=StateTracker();c._signature=()
        c.client=Mock();c.refresh_guides=Mock();c.recalculate=Mock();c.emit=Mock();c.times=deque()
        c.capture=Mock();c.capture.latest.return_value=(np.zeros((108,192,3),dtype=np.uint8),0)
        c.recognizer=Mock()
        def observed(image):
            c.closing=True
            return GameState(scene='准备',roles=[Seen('r','ROLE','角色','备战',confidence=1)]),[]
        c.recognizer.analyze.side_effect=observed
        with patch('currency_war_assistant.controller.frames_stable',return_value=True),patch('currency_war_assistant.controller.time.sleep'):
            c._loop()
        self.assertEqual(('r',),c._signature)
        c.refresh_guides.assert_not_called();c.client.list_page.assert_not_called()
        c.recalculate.assert_called_once()
