# Instrument Splitter
## Description
Instrument Splitter is a Python script designed to separate vocal tracks from instruments in an audio file. It uses machine learning models to perform this separation accurately, saving the resulting tracks in distinct folders.

## Operation
After running the script, audio files are processed and divided into multiple stems:
- **vocals/**: Contains only the vocals
- **drums/**: Contains only the drums
- **bass/**: Contains only the bass
- **other/**: Contains other instruments
- **piano/****: Contains only piano (with htdemucs_6s model)
- **guitar/**: Contains only guitar (with htdemucs_6s model)

Resulting structure:
```
|-- instrument_splitter.py
|-- requirements.txt
|-- separated_audio/
    |-- vocals/
    |-- drums/
    |-- bass/
    |-- other/
    |-- piano/     (htdemucs_6s model)
    |-- guitar/     (htdemucs_6s model)
|-- venv/
```

### 1. Creating the Working Directory
Create a dedicated folder to place the script. For example: Instrument_Splitter

### 2. Installation
1. Navigate to the newly created folder and open the terminal.
2. Download the repository:
```sh
git clone git@github.com:holms/py-instrument-splitter.git
```

### 3. Creating the Virtual Environment and Installing Dependencies
```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Installing Torch
Depending on your system configuration, you need to manually install the correct version of Torch:

#### **For NVIDIA GPU**
```sh
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

#### **For CPU**
```sh
pip install torch torchvision torchaudio
```

## Usage
Make sure the virtual environment is active, navigate to the main directory and run:

```sh
source venv/bin/activate
python3 instrument_splitter.py
```

## License
This project is open-source and must remain free for all users. Contributions and improvements are welcome!
