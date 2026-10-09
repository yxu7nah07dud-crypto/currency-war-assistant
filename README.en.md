# Currency War Assistant

Languages: [中文](README.md) · **English** · [日本語](README.ja.md)

An unofficial Windows 10/11 desktop companion for the Currency War mode in *Honkai: Star Rail*. It observes the game window locally, recognizes visible roles, shop cards, equipment and economy values, then explains public guide-code matches and the next recommended action.

## Use

1. Start the game and enter Currency War.
2. Run `CurrencyWarAssistant.exe`, choose the game window and click **Start observing**.
3. If you copied a guide code, paste it into **Guide code for this game** and click **Apply and lock**. The locked guide stays fixed until **New game**.
4. Check **What to do now** for purchases, equipment, economy and the next stage.
5. Use **Recognized** to correct uncertain roles, stars, equipment or investments.

The interface supports Chinese, English and Japanese. Settings are saved when the assistant closes. The assistant does not read game process memory, modify game files, send keyboard or mouse input, or upload screenshots.

## Public-source policy

The public source package intentionally contains no game artwork, wiki database, guide cache or copied guide text. The first refresh obtains current public configuration and guide metadata into the user's local `CurrencyWarAssistantData/cache` directory. Do not commit that directory.

This is an unofficial fan tool and is not affiliated with miHoYo, HoYoverse, HoYoLAB or *Honkai: Star Rail*. Game names, artwork, data and guide content belong to their respective rights holders. See [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE).

## Development

Python 3.12, Tkinter, Windows Graphics Capture, RapidOCR/ONNX Runtime and OpenCV.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

For the complete Chinese usage guide, see [README.md](README.md).
