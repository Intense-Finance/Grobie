#!/usr/bin/env python3
# Copyright (c) 2026 INTENSE FINANCE, LLC
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version. See LICENSE-GPLv3.txt in this tools package, or
# https://grobie.slopcore.army/tools/LICENSE-GPLv3.txt
#
"""grobie-voice: offline Grobie speech (style-matched, NOT a voice clone).
Usage: grobie-voice "text" -o out.wav [--preset death-deep] [--mp3]
       [--autotune KEY] [--retune 0..1] [--chorus [DEPTH]] [--chords] [--echo]
       [--engine piper --piper-voice en_US-norman-medium] [--raw]
"""
import argparse, json, math, os, re, sys, subprocess, tempfile, wave
import numpy as np, soundfile as sf, parselmouth
from parselmouth.praat import call
from pedalboard import (Pedalboard, HighpassFilter, LowShelfFilter, PeakFilter, HighShelfFilter,
                        Distortion, Compressor, Reverb, Limiter, Gain, LowpassFilter)
HERE=os.path.dirname(os.path.abspath(__file__)); M=os.environ.get("GROBIE_VOICE_MODELS", os.path.join(HERE,"models"))
SR=24000
_kok=None
def kokoro(text,p):
    global _kok
    from kokoro_onnx import Kokoro
    if _kok is None: _kok=Kokoro(os.path.join(M,"kokoro-v1.0.onnx"),os.path.join(M,"voices-v1.0.bin"))
    v=p["voice"]
    if isinstance(v,dict):  # weighted blend of built-in Kokoro style vectors
        tot=sum(v.values()); style=sum(_kok.get_voice_style(n)*w/tot for n,w in v.items()).astype(np.float32)
    else: style=v
    a,sr=_kok.create(text,voice=style,speed=p.get("speed",1.0),lang=p.get("lang","en-us"),
                     sentence_pause=p.get("sentence_pause",0.25),clause_pause=p.get("clause_pause",0.1))
    return a.astype(np.float32),sr
def piper(text,p):
    from piper import PiperVoice
    from piper.config import SynthesisConfig
    pv=PiperVoice.load(os.path.join(M,p.get("piper_voice","en_US-norman-medium")+".onnx"))
    with tempfile.NamedTemporaryFile(suffix=".wav") as t:
        with wave.open(t.name,"wb") as w:
            pv.synthesize_wav(text,w,syn_config=SynthesisConfig(length_scale=1/p.get("speed",1.0)))
        a,sr=sf.read(t.name,dtype="float32")
    return a,sr
def praat_shape(a,sr,pr):
    s=parselmouth.Sound(a.astype(np.float64),sampling_frequency=sr)
    s=call(s,"Change gender",60,300,pr["formant_ratio"],pr["pitch_median"],pr["pitch_range"],pr["duration"])
    return s.values[0].astype(np.float32)
def octave_down(a,sr):
    s=parselmouth.Sound(a.astype(np.float64),sampling_frequency=sr)
    m=call(s.to_pitch(),"Get quantile",0,0,0.5,"Hertz")
    if not np.isfinite(m): return np.zeros_like(a)
    d=call(s,"Change gender",60,300,1.0,m/2,1.0,1.0).values[0].astype(np.float32)
    d=Pedalboard([LowpassFilter(900)])(d,sr); return d[:len(a)] if len(d)>=len(a) else np.pad(d,(0,len(a)-len(d)))
def env_follow(a,sr,ms=15):
    n=max(1,int(sr*ms/1000)); return np.convolve(np.abs(a),np.ones(n)/n,mode="same")

# Leading 'a-' before a line-initial Groby: Kokoro at speed 0.6 inserts a dark
# schwa-like vowel (~180-220 ms) before /ɡɹ/, and Praat duration 1.75 stretches
# it into a clearly audible "a-". Only used when a preset sets trim_lead_murmur
# (grobie-tv-match). Other presets are unchanged. Phoneme-gated so "I am..." etc. stay intact.
_STOPS=set("ɡgbd")
def _split_units(text):
    return [u for u in re.split(r'(?<=[,.!?;:])\s*', (text or "").strip()) if u.strip()]
def _starts_voiced_stop(text, lang="en-us"):
    text=(text or "").strip()
    if not text: return False
    if _kok is not None:
        ph=_kok.tokenizer.phonemize(text, lang=lang)
        for ch in ph:
            if ch.isspace() or ch in ".,!?;:\"'‘’“”-–—()[]ˈˌˑː": continue
            return ch in _STOPS
        return False
    w=re.match(r"[^A-Za-z]*([A-Za-z]+)", text)
    return bool(w and w.group(1)[0].lower() in "gbd")
def _speech_segs(a,sr,silence_ms=200,silence_db=-42):
    hop=int(sr*0.01)
    rms=np.array([np.sqrt(np.mean(a[i:i+hop]**2)+1e-20) for i in range(0,len(a),hop)])
    silent=20*np.log10(rms/(float(rms.max())+1e-20)+1e-12)<silence_db
    need=max(1,int(silence_ms/10)); segs=[]; i=0; N=len(silent)
    while i<N:
        while i<N and silent[i]: i+=1
        if i>=N: break
        j=i
        while j<N:
            if silent[j] and j+need<=N and silent[j:j+need].all(): break
            j+=1
        segs.append((i*hop, min(len(a),j*hop))); i=j
    return segs
def _valley_cut(seg,sr,min_preamble_ms=80,search_ms=450,min_dip_db=3.5,lookback_ms=280):
    hop=int(sr*0.01)
    rms=np.array([np.sqrt(np.mean(seg[i:i+hop]**2)+1e-20) for i in range(0,len(seg),hop)])
    sm=np.convolve(20*np.log10(rms+1e-20),np.ones(3)/3,mode="same")
    if len(sm)<12: return None
    win=min(len(sm),int((search_ms+50)/10)+1)
    th=max(sm[:win].max()-35,-55); voiced=np.where(sm>th)[0]
    if not len(voiced): return None
    s0=int(voiced[0]); last=min(len(sm)-1,s0+int(search_ms/10)); need=int(min_preamble_ms/10)
    if last-s0<need+4: return None
    n2=s0+need+int(np.argmax(sm[s0+need:last+1]))
    lo=max(s0+2,n2-int(lookback_ms/10))
    if n2-lo<3: return None
    valley=lo+int(np.argmin(sm[lo:n2]))
    n1=s0+int(np.argmax(sm[s0:valley+1])) if valley>s0 else s0
    dip=float(sm[n1]-sm[valley]); rec=float(sm[n2]-sm[valley])
    if dip<min_dip_db or rec<3.0 or n2<=valley or (valley-s0)*10<min_preamble_ms: return None
    half=n1+1
    while half<valley and sm[half]>sm[n1]-0.5*dip: half+=1
    return max(0,half*hop/sr)
def trim_lead_murmur(a,sr,text="",lang="en-us",fade_ms=6):
    """Drop a line-initial schwa before /ɡ b d/, keeping a short /g/ closure so the burst is not clipped."""
    a=np.asarray(a,dtype=np.float32)
    flags=[_starts_voiced_stop(u,lang) for u in _split_units(text)]
    segs=_speech_segs(a,sr); pieces=[]; pos=0
    for i,(start,end) in enumerate(segs):
        pieces.append(a[pos:start])
        t=_valley_cut(a[start:end],sr) if (i<len(flags) and flags[i]) else None
        if t is not None:
            cut=start+int(round(t*sr)); new=a[cut:end].copy()
            fade=int(sr*fade_ms/1000)
            if fade>0 and len(new)>fade: new[:fade]*=np.linspace(0,1,fade,dtype=np.float32)
            pieces.append(new)
        else:
            pieces.append(a[start:end])
        pos=end
    pieces.append(a[pos:])
    return np.concatenate([p for p in pieces if len(p)]) if pieces else a

def process(a,sr,p,text=None):
    if p.get("trim_lead_murmur"): a=trim_lead_murmur(a,sr,text=text or "",lang=p.get("lang","en-us"))
    a=praat_shape(a,sr,p["praat"])
    out=a.copy()
    if p.get("sub_octave",0)>0: out=out+p["sub_octave"]*octave_down(a,sr)
    b=p["bot"]
    if b.get("comb_ms",0)>0:  # metallic resonance (feed-forward comb, 3 taps)
        d=int(sr*b["comb_ms"]/1000); c=np.zeros_like(out)
        for k,g in [(1,0.6),(2,0.36),(3,0.2)]: c[d*k:]+=g*out[:-d*k]
        out=out+b["comb_mix"]*c
    if b.get("ring_hz",0)>0:
        t=np.arange(len(out))/sr; out=(1-b["ring_mix"])*out+b["ring_mix"]*out*np.sin(2*np.pi*b["ring_hz"]*t)*1.6
    fx={"hp":lambda f,g=0,q=0:HighpassFilter(f),"lowshelf":lambda f,g,q=0.7:LowShelfFilter(f,g,q),
        "peak":lambda f,g,q=1.0:PeakFilter(f,g,q),"highshelf":lambda f,g,q=0.7:HighShelfFilter(f,g,q),"lp":lambda f,g=0,q=0:LowpassFilter(f)}
    out=Pedalboard([fx[t](*args) for t,*args in p["eq"]])(out,sr)
    if p.get("match_eq"):  # static octave-band tone match (see tune_match.py)
        out=Pedalboard([PeakFilter(f,g,1.0) for f,g in p["match_eq"] if abs(g)>0.05])(out,sr)
    g=p["grit"]
    if g["mix"]>0:
        wet=Pedalboard([Distortion(g["drive_db"]),LowpassFilter(6500)])(out,sr)
        wet*= (np.sqrt(np.mean(out**2))+1e-9)/(np.sqrt(np.mean(wet**2))+1e-9)
        out=(1-g["mix"])*out+g["mix"]*wet
    if p.get("post_eq"):
        out=Pedalboard([fx[t](*args) for t,*args in p["post_eq"]])(out,sr)
    if p.get("air_noise",0)>0:  # breath layer: noise shaped by the voice envelope
        rng=np.random.default_rng(7); n=Pedalboard([HighpassFilter(1800),LowpassFilter(9000)])(rng.standard_normal(len(out)).astype(np.float32),sr)
        n*=env_follow(out,sr); n*=(np.sqrt(np.mean(out**2))/(np.sqrt(np.mean(n**2))+1e-9))
        out=out+p["air_noise"]*n
    c=p["comp"]; r=p["reverb"]
    out=Pedalboard([Compressor(c["threshold"],c["ratio"],5,120)])(out,sr)
    out=np.concatenate([out,np.zeros(int(sr*1.2),np.float32)])  # room for the tail
    st=np.stack([out,out])
    st=Pedalboard([Reverb(room_size=r["room"],damping=r["damping"],wet_level=r["wet"],dry_level=1-r["wet"]*0.5,width=r["width"]),
                   Limiter(-1.0,100)])(st,sr)
    pk=np.abs(st).max(); st=st/pk*0.89 if pk>0 else st  # ~ -1 dBFS peak
    # trim trailing silence below -60 dB
    lv=np.abs(st).max(0); idx=np.where(lv>10**(-60/20))[0]; st=st[:, :idx[-1]+int(0.05*sr)] if len(idx) else st
    return st.T

# --- Opt-in FX. Approved recipe is the grobie-signature preset (D-minor chords, chorus, fully dry). ---
# Applied AFTER the existing preset chain (v3 mixed from a finished death-deep-dry render).
# Off unless flags or the grobie-signature preset ask for them. Echo is off by default.
_NOTE_PC={"C":0,"C#":1,"DB":1,"D":2,"D#":3,"EB":3,"E":4,"F":5,"F#":6,"GB":6,
          "G":7,"G#":8,"AB":8,"A":9,"A#":10,"BB":10,"B":11}
_MAJOR=(0,2,4,5,7,9,11); _NMINOR=(0,2,3,5,7,8,10)
_CHORUS_V3="chorus=0.6:0.8:40|55:0.35|0.3:0.25|0.3:2|1.5"
_ECHO="aecho=0.8:0.7:80:0.25"
_FINISH="areverse,silenceremove=start_periods=1:start_threshold=-55dB,areverse,apad=pad_dur=0.3,loudnorm=I=-14:TP=-1.5"
_FX_HELP=("FX (opt-in, echo off unless --echo):\n"
          "  --autotune KEY    hard-tune to a major or natural-minor key (Dm, D minor, C, F#m)\n"
          "  --retune 0..1     autotune strength (1=hard snap, default 1.0)\n"
          "  --chorus [DEPTH]  detuned chorus, no echo tail (default depth = approved signature)\n"
          "  --chords          diatonic third, fifth and sub-octave (implies --autotune, default key Dm)\n"
          "  --echo            short echo (off by default)")

def parse_key(s):
    t=re.sub(r"natural","",re.sub(r"\s+","",s.strip()),flags=re.I)
    m=re.fullmatch(r"([A-Ga-g](?:#|b)?)(.*)",t)
    if not m: raise ValueError("unrecognized key %r (try Dm, D minor, C, F#m)"%s)
    note,rest=m.group(1).upper(),m.group(2).lower()
    if note not in _NOTE_PC: raise ValueError("unrecognized note %r in key %r"%(m.group(1),s))
    if rest in ("","maj","major"): minor=False
    elif rest in ("m","min","minor"): minor=True
    else: raise ValueError("unrecognized key %r (try Dm, D minor, C, F#m)"%s)
    root=_NOTE_PC[note]; iv=_NMINOR if minor else _MAJOR
    return [(root+i)%12 for i in iv]

def chorus_expr(depth):
    if depth is True: depth=1.0
    depth=float(depth)
    return _CHORUS_V3 if depth==1.0 else "chorus=0.6:0.8:40|55:0.35|0.3:0.25|0.3:%g|%g"%(2.0*depth,1.5*depth)

def praat_tune(snd, scale, steps=0, octave=0, strength=1.0):
    """Praat Manipulation hard-tune (same method as voice-work/groby/autotune.py and chords.py)."""
    notes=sorted(m for m in range(24,96) if m%12 in scale)
    man=call(snd,"To Manipulation",0.01,60,300)
    pt=call(man,"Extract pitch tier")
    n=call(pt,"Get number of points")
    newpt=call("Create PitchTier","t",snd.xmin,snd.xmax)
    strength=float(strength)
    for i in range(1,n+1):
        t=call(pt,"Get time from index",i)
        f=call(pt,"Get value at index",i)
        midi=69+12*math.log2(f/440.0)
        idx=min(range(len(notes)),key=lambda k,midi=midi: abs(notes[k]-midi))
        if strength==1.0:
            m=notes[idx+steps]+12*octave
        else:
            j=min(max(idx+steps,0),len(notes)-1)
            hard=notes[j]+12*octave
            m=midi+strength*(hard-midi)
        call(newpt,"Add point",t,440.0*2**((m-69)/12))
    call([man,newpt],"Replace pitch tier")
    return call(man,"Get resynthesis (overlap-add)")

def mix_filter(n_voices, chorus=None, echo=False):
    if n_voices==4:
        head=("[0:a]volume=1.0,pan=stereo|c0=c0|c1=c0[r];"
              "[1:a]adelay=12|12,volume=0.6,pan=stereo|c0=0.8*c0|c1=0.4*c0[t];"
              "[2:a]adelay=20|20,volume=0.55,pan=stereo|c0=0.4*c0|c1=0.8*c0[f];"
              "[3:a]volume=0.4,pan=stereo|c0=c0|c1=c0[s];"
              "[r][t][f][s]amix=inputs=4:normalize=0")
    else:
        head="[0:a]aformat=channel_layouts=stereo"
    tail=""
    if chorus not in (None, False, 0, 0.0): tail+=","+chorus_expr(chorus)
    if echo: tail+=","+_ECHO
    return head+","+_FINISH if not tail else head+tail+","+_FINISH

def run_ffmpeg(inputs, filt, out_wav=None, out_mp3=None):
    base=["ffmpeg","-y","-loglevel","error"]
    for p in inputs: base+=["-i",p]
    base+=["-filter_complex",filt]
    # Two passes on purpose: the approved v3 mp3 is the direct filter->lame 192k encode.
    # Going wav-then-mp3 is not bit-identical to that encode.
    if out_wav:
        subprocess.run(base+["-ar","44100","-c:a","pcm_s16le",out_wav],check=True)
    if out_mp3:
        subprocess.run(base+["-ar","44100","-c:a","libmp3lame","-b:a","192k",out_mp3],check=True)

def fx_active(fx):
    if not fx: return False
    ch=fx.get("chorus")
    return bool(fx.get("autotune") or fx.get("chords") or fx.get("echo") or (ch not in (None, False, 0, 0.0)))

def collect_fx(preset, args):
    fx=dict(preset.get("fx") or {})
    if args.autotune is not None: fx["autotune"]=args.autotune
    if args.chords: fx["chords"]=True
    if args.chorus is not None: fx["chorus"]=args.chorus
    if args.echo: fx["echo"]=True
    if args.retune is not None: fx["retune"]=args.retune
    if fx.get("chords") and not fx.get("autotune"): fx["autotune"]="Dm"
    return fx

def apply_fx(y, sr, fx, out_wav, out_mp3=None):
    autokey=fx.get("autotune")
    chords=bool(fx.get("chords"))
    chorus=fx.get("chorus")
    echo=bool(fx.get("echo"))
    strength=float(fx.get("retune",1.0))
    if not (0.0<=strength<=1.0):
        raise ValueError("--retune must be between 0 and 1 (got %s)"%strength)
    scale=parse_key(autokey) if autokey else None
    os.makedirs(os.path.dirname(os.path.abspath(out_wav)),exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="grobie-fx-") as td:
        dry=os.path.join(td,"dry.wav")
        sf.write(dry,y,sr,subtype="PCM_16")
        if scale is not None:
            snd=parselmouth.Sound(dry)
            voices=[("root",0,0)]+([("third",2,0),("fifth",4,0),("sub",0,-1)] if chords else [])
            inputs=[]
            for name,steps,octv in voices:
                path=os.path.join(td,name+".wav")
                stem=praat_tune(snd,scale,steps,octv,strength)
                # v3 saved 16-bit WAV (bit-exact when nothing clips). If overlap-add peaks above 1, keep the full float.
                if float(np.max(np.abs(stem.values)))<=1.0:
                    stem.save(path,"WAV")
                else:
                    x=stem.values[0].astype(np.float32) if stem.n_channels==1 else stem.values.T.astype(np.float32)
                    sf.write(path,x,int(round(stem.sampling_frequency)),subtype="FLOAT")
                inputs.append(path)
        else:
            inputs=[dry]
        run_ffmpeg(inputs, mix_filter(len(inputs), chorus=chorus, echo=echo),
                   out_wav=out_wav, out_mp3=out_mp3)
    y2,sr2=sf.read(out_wav,dtype="float32")
    return y2,sr2

def main():
    ap=argparse.ArgumentParser(
        description="Offline Grobie voice (style-matched, not a clone).",
        epilog=_FX_HELP, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text",nargs="?"); ap.add_argument("-f","--file",help="read text from file")
    ap.add_argument("-o","--out"); ap.add_argument("--preset",default="death-deep")
    ap.add_argument("--mp3",action="store_true",help="also write an .mp3 next to the .wav (or give -o x.mp3). Signature/FX mp3s are 44.1 kHz 192k CBR; otherwise -q:a 2.")
    ap.add_argument("--engine",choices=["kokoro","piper"]); ap.add_argument("--piper-voice")
    ap.add_argument("--raw",action="store_true",help="skip post-processing")
    ap.add_argument("--list",action="store_true",help="list presets and FX options")
    ap.add_argument("--autotune",metavar="KEY",help="hard-tune to a key (Dm, D minor, C, F#m). Major and natural minor.")
    ap.add_argument("--retune",type=float,default=None,metavar="0..1",
                    help="autotune strength 0..1 (1=hard snap, default 1.0)")
    ap.add_argument("--chorus",nargs="?",const=1.0,type=float,metavar="DEPTH",
                    help="chorus (optional depth; default matches the approved signature). No echo tail.")
    ap.add_argument("--chords",action="store_true",
                    help="stack diatonic third, fifth and sub-octave in the autotune key (implies --autotune, default key Dm)")
    ap.add_argument("--echo",action="store_true",help="add a short echo (off by default)")
    a=ap.parse_args()
    P=json.load(open(os.path.join(HERE,"presets.json")))
    if a.list:
        for k,v in P.items(): print(f"{k:16s} {v['about']}")
        print()
        print(_FX_HELP)
        return
    text=open(a.file).read() if a.file else a.text
    if not text or not a.out: ap.error("give text (or -f file) and -o out.wav")
    if a.preset not in P: ap.error("unknown preset %r (try --list)"%a.preset)
    if a.retune is not None and not (0.0<=a.retune<=1.0):
        ap.error("--retune must be between 0 and 1")
    lex=os.path.join(HERE,"pronounce.json")  # optional spelling fixes, e.g. {"Grobie": "Groby"}
    if os.path.exists(lex):
        for w,r in json.load(open(lex)).items(): text=re.sub(r"\b%s\b"%re.escape(w),r,text)
    p=dict(P[a.preset])
    if a.engine: p["engine"]=a.engine
    if a.piper_voice: p["piper_voice"]=a.piper_voice
    lic=str(p.get("license","") or p.get("voice_license","")).lower()
    if p["engine"]=="piper" and ("nc-sa" in lic or "non-commercial" in lic or "noncommercial" in lic or p.get("commercial") is False):
        sys.exit("This Piper voice is marked non-commercial and is not allowed for store or commercial use.")
    try:
        fx=collect_fx(p,a)
        if fx.get("autotune"): parse_key(fx["autotune"])
    except ValueError as e:
        ap.error(str(e))
    if a.retune is not None and not (fx.get("autotune") or fx.get("chords")):
        ap.error("--retune requires --autotune or --chords (or the grobie-signature preset)")
    audio,sr=(kokoro if p["engine"]=="kokoro" else piper)(text,p)
    out=a.out; wav=out if out.lower().endswith(".wav") else os.path.splitext(out)[0]+".wav"
    os.makedirs(os.path.dirname(os.path.abspath(wav)),exist_ok=True)
    want_mp3=bool(a.mp3 or out.lower().endswith(".mp3"))
    mp3=os.path.splitext(wav)[0]+".mp3" if want_mp3 else None
    if a.raw:
        y=audio
        sf.write(wav,y,sr,subtype="PCM_16")
        if want_mp3:
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",wav,"-codec:a","libmp3lame","-q:a","2",mp3],check=True)
    elif fx_active(fx):
        y=process(audio,sr,p,text=text)
        apply_fx(y,sr,fx,out_wav=wav,out_mp3=mp3)
    else:
        y=process(audio,sr,p,text=text)
        sf.write(wav,y,sr,subtype="PCM_16")
        if want_mp3:
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",wav,"-codec:a","libmp3lame","-q:a","2",mp3],check=True)
    if want_mp3: print(mp3)
    print(wav)
if __name__=="__main__": main()
