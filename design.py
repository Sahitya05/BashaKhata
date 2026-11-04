"""Presentation components. User-provided text is escaped before rendering."""
from html import escape
from pathlib import Path
import streamlit as st


def install_styles():
    st.html("<style>" + Path(__file__).with_name("styles.css").read_text(encoding="utf-8") + "</style>")


def voice_sculpture():
    st.html("""
    <div class="voice-scene" aria-hidden="true">
      <div class="voice-halo"></div>
      <div class="voice-disc"></div>
      <div class="voice-mic">
        <div class="mic-head"><i></i><i></i><i></i><i></i></div>
        <div class="mic-cradle"></div><div class="mic-stem"></div><div class="mic-foot"></div>
      </div>
      <div class="voice-token token-one">₹</div><div class="voice-token token-two">✓</div>
      <div class="voice-floor"></div>
    </div>
    """)


def guide_cards(labels):
    st.html('<div class="guide-cards">' + ''.join(
        f'<div class="guide-card"><span>{number:02d}</span><p>{escape(text)}</p></div>'
        for number, text in enumerate(labels, 1)
    ) + '</div>')


def balance_card(title, value, symbol, index):
    st.html(
        f'<article class="balance-card balance-{index}">'
        f'<div class="balance-top"><span>{escape(title)}</span>'
        f'<span class="balance-icon" aria-hidden="true">{escape(symbol)}</span></div>'
        f'<div class="balance-value">{escape(value)}</div>'
        '<div class="balance-rail" aria-hidden="true"></div></article>'
    )


def waveform():
    st.html('<div class="bk-wave bk-dashboard-wave" aria-hidden="true">' +
            ''.join(f'<i style="--height:{height}px;--delay:{index * .1}s"></i>'
                    for index, height in enumerate([5, 8, 12, 18, 25, 15, 30, 38, 24, 40, 32, 20, 14, 25, 18, 10, 6])) +
            '</div>')


def masthead(description):
    st.html(
        '<section class="bk-hero"><div class="bk-copy">'
        '<span class="bk-eyebrow">BHASHAKHATA · VOICE LEDGER</span>'
        '<h1>Your words.<br><em>Your business.</em></h1>'
        f'<p>{escape(description)}</p>'
        '<div class="bk-tags"><span>తెలుగు</span><span>हिन्दी</span><span>English</span></div>'
        '</div><div class="bk-art" aria-hidden="true"><div class="bk-orbit"></div>'
        '<div class="bk-paper"><span class="bk-paper-label">BHASHAKHATA</span>'
        '<div class="bk-wave">' +
        ''.join(f'<i style="--height:{height}px;--delay:{index * .12}s"></i>'
                for index, height in enumerate([14, 25, 40, 60, 32, 78, 48, 25, 55, 38, 20])) +
        '</div><div class="bk-rule"></div><div class="bk-rule short"></div>'
        '<div class="bk-seal">✓</div></div></div></section>'
    )


def steps(active, labels):
    st.html('<nav class="bk-steps" aria-label="Transaction progress">' + ''.join(
        f'<div class="bk-step {"active" if index == active else ""}"'
        + (' aria-current="step"' if index == active else '') + '>'
        f'<span>{index:02d}</span><strong>{escape(text)}</strong></div>'
        for index, text in enumerate(labels, 1)
    ) + '</nav>')
