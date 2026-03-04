import subprocess
import json
import os
import re
import glob
import concurrent.futures
import multiprocessing

def sanitize_filename(name):
    """Illegal characters remove karta hai"""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def get_chapters(filename):
    """FFprobe se chapter metadata nikalta hai"""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_chapters", filename
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ FFprobe run nahi hua properly for '{filename}'.")
            return []
        data = json.loads(result.stdout)
        return data.get("chapters", [])
    except Exception as e:
        print(f"❌ Metadata read nahi ho paya for '{filename}':", e)
        return []

def extract_single_chapter(chapter, i, input_file, output_folder):
    """Ek single chapter ko cut karne ka function"""
    start_time = chapter["start_time"]
    end_time = chapter["end_time"]
    meta_title = chapter.get("tags", {}).get("title", "")

    if meta_title:
        safe_title = sanitize_filename(meta_title)
        if safe_title.isdigit():
            file_name = f"Chapter_{i+1:02d}.m4a"
        else:
            file_name = f"Chapter_{i+1:02d}_{safe_title}.m4a"
    else:
        file_name = f"Chapter_{i+1:02d}.m4a"

    output_path = os.path.join(output_folder, file_name)
    
    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-ss", str(start_time), "-to", str(end_time),
        "-c", "copy", output_path
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return file_name

def process_audiobook(input_file):
    """Audiobook process karne ka main function"""
    base_name = os.path.splitext(input_file)[0]
    output_folder = sanitize_filename(base_name)

    print(f"\n🔍 Reading '{input_file}'...")
    chapters = get_chapters(input_file)

    if not chapters:
        print(f"⚠️ Bhai, '{input_file}' mein chapters nahi mile! Skipping...")
        return

    # Codespace ke 4 cores ka full use, safely.
    optimal_threads = min(4, multiprocessing.cpu_count())
    print(f"✅ {len(chapters)} chapters mile. Firing up {optimal_threads} cores! 🚀")
    os.makedirs(output_folder, exist_ok=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=optimal_threads) as executor:
        futures = [
            executor.submit(extract_single_chapter, chapter, i, input_file, output_folder) 
            for i, chapter in enumerate(chapters)
        ]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                completed_file = future.result()
                print(f"   ⚡ Done: {completed_file}")
            except Exception as exc:
                print(f"   ❌ Ek chapter fail ho gaya: {exc}")

    print(f"🎉 Bawal chiz! '{output_folder}' ready hai.")

def main():
    print("🚀 Script Codespace mode mein start ho rahi hai...")
    m4b_files = glob.glob("*.m4b")
    
    if not m4b_files:
        print("🛑 Arey yaar, ek bhi .m4b file nahi hai current folder mein.")
        return
        
    print(f"📦 Total {len(m4b_files)} audiobook(s) mili. Let's go!\n")
    
    for file in m4b_files:
        process_audiobook(file)
        
    print("\n🏆 Sab khatam! Server ki aukaat ke hisaab se optimal run.")

if __name__ == "__main__":
    main()