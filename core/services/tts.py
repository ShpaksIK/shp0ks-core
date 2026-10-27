import queue
import threading
import pyttsx3

class TTS:
    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _worker(self):
        engine = pyttsx3.init()
        
        engine.setProperty('rate', 180)
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[0].id)

        while True:
            text = self._queue.get()
            if text is None:
                break
            
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass
            
            self._queue.task_done()

    def say(self, text: str):
        """Добавляет текст в очередь на озвучку."""
        if text:
            self._queue.put(text)

tts = TTS()