# Currency War Assistant

Investment environment and strategy screens show a preferred option and comparisons of effects, lineup relevance and trigger conditions. Without a locked guide or confirmed lineup, only general resource rules are used. A locked guide supplies its author's preferences. Incomplete recognition is marked provisional; add missing offered cards in **Recognized**. Refreshing or leaving the page clears offered choices. Manually mark the card you actually picked as selected.

Languages: [中文](README.md) · **English** · [日本語](README.ja.md)

An unofficial Windows 10/11 desktop companion for the Currency War mode in *Honkai: Star Rail*. It observes the game window locally, recognizes visible roles, shop cards, equipment and economy values, then explains public guide-code matches and the next recommended action.

## Guide lookup and cache coverage (v1.0.3)

Paste a raw code or the complete game share text, then choose **Apply & lock**. A missing cached code triggers online pagination and an exact check against official guide details. **Read clipboard** retains the title so trait filters can speed up lookup. A guide locks as soon as found; full sync can continue in the background. Unlocking or starting a new game cancels a pending lookup.

**Update guides** follows every available page of both Hot and Latest public recommendations for ordinary mode and deduplicates their results. Earlier versions only read the first three pages of each order (about 60 guides). The footer now reports pages, cached guides, entries with codes, and sync status. Interrupted sync retains results and resumes at the saved page. A first sync can take several minutes.

“Public recommendation snapshot read to the end” appears only after both lists end. This covers this snapshot of the ordinary-mode public API, not every historical, private, deleted, or game-context-specific guide. Cached information may be incomplete or outdated. If a code is missing, retry the complete share text with its title. Expired guides cannot be locked; older guides still require checking current roles, equipment and author prerequisites. Lookup status remains visible independently of observation messages.

## Use

1. Start the game and enter Currency War.
2. Run `CurrencyWarAssistant.exe`, choose the game window and click **Start observing**.
3. If you copied a guide code, paste it into **Guide code for this game** and click **Apply and lock**. The locked guide stays fixed until **New game**.
4. Check **What to do now** for purchases, equipment, economy and the next stage.
5. Use **Recognized** to correct uncertain roles, stars, equipment or investments.
6. Open **Settings** above the header to adjust always-on-top, borderless window, opacity, language and theme. Settings are saved when you close the assistant.
7. Enable **Borderless window** to hide the assistant's native title bar. Drag its header to move it, and the bottom-right triangle to resize. Use **−** to minimize and **×** to close. Press **Esc** or untick the setting to restore the frame. This switch only changes the assistant window.

The interface supports Chinese, English and Japanese. Settings are saved when the assistant closes. The assistant does not read game process memory, modify game files, send keyboard or mouse input, or upload screenshots.

## Updating and capture errors

Keep `CurrencyWarAssistant.exe` beside the complete `_internal` directory. Version 1.0.2 explicitly bundles the native capture component and checks real capture in the packaged application. If an older version reports `No module named 'windows_capture.windows_capture'`, close it and extract the complete new release into a new folder. Replacing only the executable is insufficient. Move your previous `CurrencyWarAssistantData` folder into the new folder to keep settings and cache. Borderless display cannot repair missing components.

The assistant's borderless setting and the game's display mode are independent. If the captured game image is black, try the game's windowed or borderless display mode. See [CHANGELOG.md](CHANGELOG.md).

## Public-source policy

The public source package intentionally contains no game artwork, wiki database, guide cache or copied guide text. The first refresh obtains current public configuration and guide metadata into the user's local `CurrencyWarAssistantData/cache` directory. Do not commit that directory.

This is an unofficial fan tool and is not affiliated with miHoYo, HoYoverse, HoYoLAB or *Honkai: Star Rail*. Game names, artwork, data and guide content belong to their respective rights holders. See [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE).

## Development

Python 3.12, Tkinter, Windows Graphics Capture, RapidOCR/ONNX Runtime and OpenCV.

```powershell
python -m venv .venv
.venv\Scripts\python.exe tools\prepare_capture_wheel.py --install
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe main.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m PyInstaller --noconfirm assistant.spec
.venv\Scripts\python.exe tools\verify_release.py
```

The release check runs the packaged executable and captures only its own synthetic test window. It does not operate the game or save game screenshots.

For the complete Chinese usage guide, see [README.md](README.md).

The public build includes no icon templates. OCR reads shop card titles; front/back/bench roles and inventory equipment require manual recognition correction or locally learned icons. Earlier portrait/star checks used private or learned templates and do not establish recognition capability in a fresh public build.

Use tools/prepare_capture_wheel.py --install before installing requirements. It creates windows-capture 2.0.1+cwa.headless1 from the official wheel, changing only its dependency metadata and local distribution version. Python sources/native binaries and original notices are retained. One headless OpenCV serves capture and OCR. The local version in the lock file must be generated with this script, not fetched from PyPI.

Recognition currently supports only the Simplified Chinese game client. English/Japanese are assistant interface and generated-advice languages. Official names, effects and guide prose stay in source Chinese. After a complete sync, updates within 24 hours read three Hot pages plus Latest until a fully cached page; owned-role changes fetch missing candidate details only. Two full absences retire an unlocked cached guide. See REVIEW-CHECKLIST.md for verification.
