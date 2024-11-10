EXTENDED_LOGGING = False

# Set to 0 to deactivate writing to keyboard
WRITE_TO_KEYBOARD_INTERVAL = 0.002

if __name__ == '__main__':

    from install_packages import check_and_install_packages
    check_and_install_packages([
        {'import_name': 'rich'},
        {'import_name': 'pyautogui'},
        {'import_name': 'sounddevice'}
    ])

    if EXTENDED_LOGGING:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    from rich.console import Console
    from rich.live import Live
    from rich.text import Text
    from rich.panel import Panel
    import os
    import sys
    from RealtimeSTT import AudioToTextRecorder
    from colorama import Fore, Style
    import colorama
    import pyautogui
    import sounddevice as sd

    # Initialize Rich Console
    console = Console()
    console.print("System initializing, please wait")

    if os.name == "nt" and (3, 8) <= sys.version_info < (3, 99):
        from torchaudio._extension.utils import _init_dll_path
        _init_dll_path()

    colorama.init()

    # Initialize Rich Live
    live = Live(console=console, refresh_per_second=10, screen=False)
    live.start()

    full_sentences = []
    rich_text_stored = ""
    recorder = None
    displayed_text = ""
    prev_text = ""

    end_of_sentence_detection_pause = 0.45
    unknown_sentence_detection_pause = 0.7
    mid_sentence_detection_pause = 2.0

    def clear_console():
        os.system('clear' if os.name == 'posix' else 'cls')

    def preprocess_text(text):
        text = text.lstrip()
        if text.startswith("..."):
            text = text[3:]
        text = text.lstrip()
        if text:
            text = text[0].upper() + text[1:]
        return text

    def text_detected(text):
        global prev_text, displayed_text, rich_text_stored

        text = preprocess_text(text)
        sentence_end_marks = ['.', '!', '?', '。']
        if text.endswith("..."):
            recorder.post_speech_silence_duration = mid_sentence_detection_pause
        elif text and text[-1] in sentence_end_marks and prev_text and prev_text[-1] in sentence_end_marks:
            recorder.post_speech_silence_duration = end_of_sentence_detection_pause
        else:
            recorder.post_speech_silence_duration = unknown_sentence_detection_pause

        prev_text = text

        rich_text = Text()
        for i, sentence in enumerate(full_sentences):
            style = "yellow" if i % 2 == 0 else "cyan"
            rich_text += Text(sentence, style=style) + Text(" ")

        if text:
            rich_text += Text(text, style="bold yellow")

        new_displayed_text = rich_text.plain

        if new_displayed_text != displayed_text:
            displayed_text = new_displayed_text
            panel = Panel(rich_text, title="[bold green]Live Transcription[/bold green]", border_style="bold green")
            live.update(panel)
            rich_text_stored = rich_text

    def process_text(text):
        global recorder, full_sentences, prev_text
        recorder.post_speech_silence_duration = unknown_sentence_detection_pause

        text = preprocess_text(text).rstrip()
        if text.endswith("..."):
            text = text[:-2]

        if not text:
            return

        full_sentences.append(text)
        prev_text = ""
        text_detected("")

        if WRITE_TO_KEYBOARD_INTERVAL:
            pyautogui.write(f"{text} ", interval=WRITE_TO_KEYBOARD_INTERVAL)

    # List available audio devices
    console.print("Listing available audio devices:", style="bold yellow")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        console.print(f"[{i}] {device['name']}")

    # Set the input device to the virtual audio device index (e.g., VB-Cable)
    virtual_audio_device_index = int(input("Enter the device index for the virtual audio device: "))

    # Recorder configuration
    recorder_config = {
        'spinner': False,
        'model': 'tiny',
        'realtime_model_type': 'tiny',
        'allowed_latency_limit': 1000,
        'language': '',
        'silero_sensitivity': 0.05,
        'webrtc_sensitivity': 3,
        'post_speech_silence_duration': unknown_sentence_detection_pause,
        'min_length_of_recording': 1.1,
        'min_gap_between_recordings': 0,
        'enable_realtime_transcription': True,
        'realtime_processing_pause': 0.02,
        'on_realtime_transcription_update': text_detected,
        'silero_deactivity_detection': True,
        'early_transcription_on_silence': 0,
        'beam_size': 5,
        'beam_size_realtime': 3,
        'no_log_file': True,
        'initial_prompt': (
            "End incomplete sentences with ellipses.\n"
            "Examples:\n"
            "Complete: The sky is blue.\n"
            "Incomplete: When the sky...\n"
            "Complete: She walked home.\n"
            "Incomplete: Because he...\n"
        ),
        'input_device_index': virtual_audio_device_index
    }

    if EXTENDED_LOGGING:
        recorder_config['level'] = logging.DEBUG

    recorder = AudioToTextRecorder(**recorder_config)

    initial_text = Panel(Text("Listening...", style="cyan bold"), title="[bold yellow]Waiting for Input[/bold yellow]", border_style="bold yellow")
    live.update(initial_text)

    try:
        while True:
            recorder.text(process_text)
    except KeyboardInterrupt:
        live.stop()
        console.print("[bold red]Transcription stopped by user. Exiting...[/bold red]")
        exit(0)
