#!/usr/bin/env python3
import os
import subprocess
import re
from pathlib import Path

def get_duration_safe(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    try:
        return float(subprocess.run(cmd, stdout=subprocess.PIPE, text=True).stdout.strip())
    except ValueError:
        return -1.0

def process_audiobook(input_file):
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"[X] Bhai file hi nahi mili: {input_file}")
        return

    folder_name = input_path.stem
    os.makedirs(folder_name, exist_ok=True)
    clean_file = Path(folder_name) / f"CLEAN_{folder_name}.mp3"

    print("\n========================================")
    print(" STAGE 1: THE 'WASHING MACHINE' (REPAIR) ")
    print("========================================")
    
    if clean_file.exists() and get_duration_safe(str(clean_file)) > 0:
        print("[*] Sahi salamat CLEAN file already exist karti hai. Time bacha rahe hain!")
    else:
        print(f"[*] Tera format {input_path.suffix} hai. Isko pehle naha-dhula ke perfect MP3 bana raha hoon.")
        print("[*] Relax kar, live progress dekh aur chai pee...")
        cmd_clean = [
            "ffmpeg", "-y", "-v", "info", "-stats", "-err_detect", "ignore_err",
            "-i", str(input_path),
            "-map", "0:a", "-c:a", "libmp3lame", "-b:a", "128k",
            str(clean_file)
        ]
        subprocess.run(cmd_clean)
        print("\n[*] Universal MP3 Ready! Ab koi bug nahi aayega.")

    print("\n========================================")
    print(" STAGE 2: THE CLIMAX (SMART vs HARD CUT) ")
    print("========================================")
    
    total_duration = get_duration_safe(str(clean_file))
    if total_duration <= 0:
        print("[X] Bhai file convert hone ke baad bhi ded hai. Sorry!")
        return

    print("[*] Audio scan chal raha hai. Background noise/silence check kar rahe hain...")
    cmd_silence = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(clean_file), "-af", "silencedetect=noise=-25dB:d=1.0", "-f", "null", "-"]
    res = subprocess.run(cmd_silence, stderr=subprocess.PIPE, text=True)
    
    silences = []
    for line in res.stderr.splitlines():
        if "silence_end" in line:
            m = re.search(r"silence_end:\s*([0-9\.]+)\s*\|\s*silence_duration:\s*([0-9\.]+)", line)
            if m:
                silences.append(float(m.group(1)) - (float(m.group(2)) / 2))
                
    print(f"[*] Total {len(silences)} pauses mile hain.")

    # ---------------------------------------------------------
    # THE MASTER LOGIC SWITCH
    # ---------------------------------------------------------
    if len(silences) > 20:
        print("[*] MODE: SMART CUT (Silences mil gaye). 45-90 min window use hogi.")
        
        min_len = 2700; target_len = 3600; max_search = 5400
        cut_points = [0.0]; current_time = 0.0

        while current_time + min_len < total_duration:
            search_start = current_time + min_len
            search_end = min(current_time + max_search, total_duration)
            valid_silences = [s for s in silences if search_start <= s <= search_end]

            if valid_silences:
                cut_point = valid_silences[-1]
            else:
                cut_point = min(current_time + target_len, total_duration)

            cut_points.append(cut_point)
            current_time = cut_point

        if total_duration - cut_points[-1] < 300 and len(cut_points) > 1:
            cut_points[-1] = total_duration
        elif cut_points[-1] < total_duration:
            cut_points.append(total_duration)

        print(f"\n[*] Total {len(cut_points)-1} parts banenge. Processing shuru...")
        segment_times = ",".join([str(round(p, 2)) for p in cut_points[1:-1]])
        out_pattern = os.path.join(folder_name, f"{folder_name}_Part_%02d.mp3")
        
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(clean_file), "-f", "segment", "-segment_times", segment_times, "-segment_start_number", "1", "-c", "copy", out_pattern]
        subprocess.run(cmd)

    else:
        print("[*] MODE: HARD CUT (No silences). Exact 1 hour cut with 3 seconds overlap!")
        
        chunk_len = 3600 # 1 hour
        overlap = 3      # 3 seconds ka jugad
        current_start = 0.0
        part_num = 1
        
        while current_start < total_duration:
            # End time fix kiya taaki original duration cross na kare
            end_time = min(current_start + chunk_len, total_duration)
            out_file = os.path.join(folder_name, f"{folder_name}_Part_{part_num:02d}.mp3")
            
            print(f"    -> Cutting Part {part_num}: {current_start/60:.1f}m to {end_time/60:.1f}m (Overlap active)")
            
            # Fast seek (-ss) with clean file is 100% bug-free!
            cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", str(current_start), "-i", str(clean_file), "-t", str(end_time - current_start), "-c", "copy", out_file]
            subprocess.run(cmd)
            
            # Next part pichle part se 3 second pehle shuru hoga
            current_start = end_time - overlap
            part_num += 1
            
            # Agar aakhiri tukda 10 second se bhi chota bacha ho, toh ignore maar do
            if current_start >= total_duration - 10:
                break

    print(f"\n[+] BOOYAH! Kaam 25 hai. '{folder_name}' folder mein tera khazana ready hai!\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Aise run kar: python parts_maker.py 'Book Name.m4a'")
    else:
        process_audiobook(sys.argv[1])