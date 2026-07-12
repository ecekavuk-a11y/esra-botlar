#!/usr/bin/env python3
"""
Arşiv Paylaşım Botu — Caption Motoru
VIP yönlendirme, link veya VIP yazısı YOKTUR.
Sadece doğal, ateşleyici caption metinleri.
"""

import json, os, random
from datetime import datetime, timezone

CAPTION_LISTESI = [
    "az önce çektim, size özel 🔥",
    "bu gece biraz eğlendim 🌙",
    "sadece sizin için çektim 🍯",
    "iyi geceler 🔥 ya da daha iyi mi yapalım?",
    "canım sıkıldı, sizi düşündüm 🌹",
    "yeni video sıcacık 🔥",
    "bugün biraz cesurduk 🍯",
    "sizi izlerken bile azdım 😈",
    "dudaklarım sizi arıyor 💋",
    "bu gece yalnız değilim, siz varsınız aklımda 🔥",
    "vücudum sizin emrinde bu gece 👅",
    "sizi içime almak istiyorum şu an 🫦",
    "bakışlarım size saplanıp kaldı 😍",
    "bu sıcakta sizi düşünmek daha da zor 🥵",
    "gözlerinizin içine bakarak çektim 😈",
    "bu karesiz kalmasın istedim 🍒",
    "size özel bir şey hissettim bugün 💋",
    "sesimi duyabilirdiniz şu an 🔥",
    "aklınızda kalmak için çektim 😜",
    "bu geceyi unutmayın 🌙",
    "hafızanıza kazımak istedim 😻",
    "sadece size bakıyorum 🫦",
    "biraz şımartmak istedim sizi 🍌",
    "gözlerinizi kapayın ve hissedin 🔥",
    "bu an sadece sizin için 👅",
    "içinizde bir şeyler hissettim 💦",
    "sizi düşündüğümde böyle oluyorum 🥵",
    "bu geceyi birlikte bitirelim 🌙",
    "dokunuşunuzu hissedebiliyorum sanki 🫦",
    "gözlerim sizde, her zaman 😍",
]

def caption_uret(idx=None):
    if idx is None:
        return random.choice(CAPTION_LISTESI)
    return CAPTION_LISTESI[idx % len(CAPTION_LISTESI)]

if __name__ == "__main__":
    for i in range(5):
        print(f"[{i}]", caption_uret(i))
