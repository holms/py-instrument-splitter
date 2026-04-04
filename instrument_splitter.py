import os
import tkinter as tk
from tkinter import filedialog
from pydub import AudioSegment
import torch
import shutil
import demucs.api
import sys
from tqdm import tqdm

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

def progress_callback(progress, pbar):
    """Progress callback for demucs separation."""
    if progress['state'] == 'segment':
        current = progress.get('segment_offset', 0)
        total = progress.get('audio_length', 1)
        pbar.n = int(current)
        pbar.total = int(total)
        pbar.set_description(f"Processing {current:.1f}s/{total:.1f}s")
        pbar.refresh()
    elif progress['state'] == 'load':
        print(f"Loading model: {progress.get('model_name', 'unknown')}")

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
        # Create progress bar
        pbar = tqdm(total=100, unit='s', desc="Loading")
        
        # Initialize Separator with model, device, and callback
        separator = demucs.api.Separator(
            model=model, 
            device=device,
            callback=lambda p: progress_callback(p, pbar)
        )
        
        pbar.set_description("Processing")
        
        # Separate audio
        print(f"Processing: {os.path.basename(input_file)}")
        origin, separated = separator.separate_audio_file(input_file)
        
        pbar.close()
        
    except Exception as e:
        print(f"Error during separation: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Process results
    track_name = os.path.splitext(os.path.basename(input_file))[0]
    
    # Create output folders and save files
    output_paths = {}
    for file, sources in separated:
        for stem, source in sources.items():
            if stem in selected_stems:
                stem_folder = os.path.join(base_output_folder, stem)
                os.makedirs(stem_folder, exist_ok=True)
                output_path = os.path.join(stem_folder, f"{track_name}_{stem}.{output_format}")
                
                # Save as wav first using demucs save_audio
                temp_wav = os.path.join(base_output_folder, f"{stem}_temp.wav")
                demucs.api.save_audio(source, temp_wav, samplerate=separator.samplerate)
                
                # Convert to desired format using pydub
                save_audio(temp_wav, output_path, output_format)
                output_paths[stem] = output_path
                
                # Cleanup temp
                os.remove(temp_wav)
    
    # Also create "no_vocals" from "other" if vocals was selected alone
    if len(selected_stems) == 1 and selected_stems[0] == "vocals":
        for file, sources in separated:
            if "other" in sources:
                no_vocals_folder = os.path.join(base_output_folder, "no_vocals")
                os.makedirs(no_vocals_folder, exist_ok=True)
                no_vocals_path = os.path.join(no_vocals_folder, f"{track_name}_no_vocals.{output_format}")
                
                temp_wav = os.path.join(base_output_folder, "other_temp.wav")
                demucs.api.save_audio(sources["other"], temp_wav, samplerate=separator.samplerate)
                save_audio(temp_wav, no_vocals_path, output_format)
                os.remove(temp_wav)
                output_paths["no_vocals"] = no_vocals_path
    
    print(f"\nAudio files saved ({output_format.upper()} format):")
    for stem, path in output_paths.items():
        print(f"- {stem.capitalize()}: {path}")
    
    print("\nSeparation complete!")

if __name__ == "__main__":
    print("=== Instrument Splitter ===")
    print("Select the audio file to separate")
    input_audio = select_audio_file()
    
    if not input_audio:
        print("No file selected. Exiting.")
    else:
        separate_audio(input_audio)