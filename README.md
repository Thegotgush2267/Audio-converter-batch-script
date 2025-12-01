# Audio Converter Batch Script

A simple Windows batch script that converts audio files using FFmpeg.

## Features
- Converts audio files using FFmpeg  
- Automatically scans the folder it's run in  
- Simple terminal menu for selecting audio files  

---

## Installation Instructions

### 1. Install FFmpeg
FFmpeg must be installed for the script to work.

1. Download FFmpeg from the official website:  
   https://ffmpeg.org/download.html
2. Extract the downloaded archive.  
3. Move the extracted folder to a safe location, for example:  
   `C:\Program Files\FFmpeg`

---

### 2. Add FFmpeg to PATH
1. Press **Win + R**, type `sysdm.cpl`, press Enter.  
2. Go to **Advanced → Environment Variables**.  
3. Under System variables, find **Path** and click Edit.  
4. Click **New** and add:  C:\Program Files\FFmpeg\bin
5. Click OK to save the changes.

---

### 3. Verify FFmpeg Installation
Open a new Command Prompt and run: ffmpeg -version

If version information appears with no errors, FFmpeg is installed correctly.

---

## How to Use
1. Make sure FFmpeg is installed and working.  
2. Run `Converter.bat`.  


---

## Enjoy
You’re ready to convert audio files easily with this batch script.




