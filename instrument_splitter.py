import os
import tkinter as tk
from tkinter import filedialog
from pydub import AudioSegment
import torch
import shutil
from demucs.api import Separator, save_audio as demucs_save_audio
import sys

def select_audio_file():
    """Opens a window to select the audio file."""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select the audio file",
        initialdir="music_input",
        filetypes=[("Audio Files", "*.mp3 *.wav *.flac *.m4a *.aac *.ogg")]
    )
    return file_path

def save_audio(input_file, output_path, format):
    """Saves the separated audio file in the specified format using pydub."""
    audio_segment = AudioSegment.from_file(input_file)
    audio_segment.export(output_path, format=format)

def choose_model():
    """Allows the user to select a model."""
    models = {
        "1": "htdemucs",
        "2": "htdemucs_6s",
        "3": "mdx_extra",
        "4": "mdx",
        "5": "light"
    }
    print("\nChoose the Demucs model:")
    print("1 - htdemucs (4 stems: drums, bass, other, vocals - High quality)")
    print("2 - htdemucs_6s (6 stems: drums, bass, other, vocals, piano, guitar)")
    print("3 - mdx_extra (4 stems - Good balance)")
    print("4 - mdx (4 stems - Trained on MusDB HQ)")
    print("5 - light (4 stems - Faster, lower quality)")
    
    while True:
        choice = input("\nEnter the model number (default: 1): ")
        if choice == "" or choice in models:
            return models.get(choice, "htdemucs")
        else:
            print("Invalid choice. Try again.")

def choose_stems(available_stems):
    """Allows user to select which stems to extract."""
    print(f"\nAvailable stems for this model: {', '.join(available_stems)}")
    print("Options:")
    print("1 - Extract ALL stems")
    print("2 - Extract only VOCALS (and instrumental)")
    print("3 - Extract only DRUMS")
    print("4 - Extract only BASS")
    print("5 - Custom selection (comma-separated, e.g., drums,bass)")
    
    while True:
        choice = input("\nEnter option (default: 1): ").strip()
        
        if choice == "" or choice == "1":
            return available_stems
        elif choice == "2":
            return ["vocals"]
        elif choice == "3":
            return ["drums"]
        elif choice == "4":
            return ["bass"]
        elif choice == "5":
            custom = input(f"Enter stems to extract (available: {', '.join(available_stems)}): ").strip().lower()
            selected = [s.strip() for s in custom.split(",")]
            # Validate
            invalid = [s for s in selected if s not in available_stems]
            if invalid:
                print(f"Invalid stems: {', '.join(invalid)}")
                continue
            return selected
        else:
            print("Invalid choice. Try again.")

def get_available_stems(model):
    """Returns the list of stems the model can separate."""
    # htdemucs_6s has 6 sources: drums, bass, other, vocals, piano, guitar
    if model == "htdemucs_6s":
        return ["drums", "bass", "other", "vocals", "piano", "guitar"]
    else:
        # Standard 4-stem models
        return ["drums", "bass", "other", "vocals"]

def progress_callback(progress_info):
    """Custom progress callback to format progress display."""
    state = progress_info.get('state', '')
    if state == 'load':
        print(f"Loading model... ({progress_info.get('model_name', 'unknown')})")
    elif state == 'segment':
        current = progress_info.get('segment_offset', 0)
        total = progress_info.get('audio_length', 1)
        # Format numbers to avoid floating-point precision issues
        current_fmt = f"{current:.1f}"
        total_fmt = f"{total:.1f}"
        percent = (current / total) * 100 if total > 0 else 0
        print(f"\rProcessing: {current_fmt}/{total_fmt}s ({percent:.1f}%)", end='', flush=True)
    elif state == 'end':
        print("\nSeparation complete!")

def separate_audio(input_file, base_output_folder="separated_audio"):
    """
    Separates instruments from an audio file using Demucs API and saves the separated tracks.
    """
    if not os.path.exists(base_output_folder):
        os.makedirs(base_output_folder)
    
    model = choose_model()
    available_stems = get_available_stems(model)
    selected_stems = choose_stems(available_stems)
    
    # Detect input format for output
    input_ext = os.path.splitext(input_file)[1].lower().lstrip('.')
    format_map = {'mp3': 'mp3', 'wav': 'wav', 'flac': 'flac', 'm4a': 'mp4', 'aac': 'aac', 'ogg': 'ogg', 'wma': 'wma'}
    output_format = format_map.get(input_ext, 'wav')
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print(f"\nSeparation in progress with model {model} on {device}...")
    print(f"Selected stems: {', '.join(selected_stems)}")
    
    try:
        # Initialize Separator with model and device
        separator = Separator(
            model=model,
            device=device,
            progress=True,
            callback=progress_callback
        )
        
        # Separate audio
        print(f"Loading and processing: {os.path.basename(input_file)}")
        wav, sr = separator.separate_audio_file(input_file)
        
    except Exception as e:
        print(f"Error during separation: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Process results
    track_name = os.path.splitext(os.path.basename(input_file))[0]
    # Find all generated stems from the wav dict returned by demucs
    generated_files = {}
    
    # wav is a dict with stem names as keys
    for stem in available_stems:
        if stem in wav:
            # Save to temp file first
            temp_wav_path = os.path.join(base_output_folder, f"{stem}_temp.wav")
            demucs_save_audio(wav[stem], temp_wav_path, sr)
            generated_files[stem] = temp_wav_path
    
    if not generated_files:
        print("Error: no separated files were found.")
        return
    
    # Create output folders for selected stems
    output_paths = {}
    for stem in selected_stems:
        if stem in generated_files:
            stem_folder = os.path.join(base_output_folder, stem)
            os.makedirs(stem_folder, exist_ok=True)
            output_path = os.path.join(stem_folder, f"{track_name}_{stem}.{output_format}")
            save_audio(generated_files[stem], output_path, output_format)
            output_paths[stem] = output_path
    
    # Also create "no_vocals" from "other" if vocals was selected alone
    if len(selected_stems) == 1 and selected_stems[0] == "vocals" and "other" in generated_files:
        no_vocals_folder = os.path.join(base_output_folder, "no_vocals")
        os.makedirs(no_vocals_folder, exist_ok=True)
        no_vocals_path = os.path.join(no_vocals_folder, f"{track_name}_no_vocals.{output_format}")
        save_audio(generated_files["other"], no_vocals_path, output_format)
        output_paths["no_vocals"] = no_vocals_path
    
    print(f"\nAudio files saved ({output_format.upper()} format):")
    for stem, path in output_paths.items():
        print(f"- {stem.capitalize()}: {path}")
    
    # Cleanup intermediate files
    for wav_path in generated_files.values():
        if os.path.exists(wav_path):
            os.remove(wav_path)
    
    print("\nSeparation complete!")

if __name__ == "__main__":
    print("=== Instrument Splitter ===")
    print("Select the audio file to separate")
    input_audio = select_audio_file()
    
    if not input_audio:
        print("No file selected. Exiting.")
    else:
        separate_audio(input_audio)