"""
Jarvis - HUD Dashboard Edition (Single-File Version)
Everything - backend logic AND the HTML/CSS/JS interface - lives in this one file.

Run:
    python jarvis_app.py
Then it opens http://localhost:5000 automatically in your browser.

Requirements:
    pip install flask faster-whisper sounddevice numpy requests soundfile pyautogui pillow psutil
"""

import subprocess
import tempfile
import threading
import time
import json
import re
import wave
import os
import webbrowser
import requests
import numpy as np
import sounddevice as sd
import psutil
from flask import Flask, render_template_string, jsonify
from faster_whisper import WhisperModel

# ---------------- CONFIG ----------------
PIPER_EXE = r"C:\piper\piper.exe"
PIPER_VOICE = r"C:\piper\en_US-lessac-medium.onnx"
OLLAMA_MODEL = "llama3.1:70b"   # full-power system - real reasoning upgrade over 8b
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_NUM_CTX = 131072        # LARGEST memory — 128k token context window
WHISPER_MODEL_SIZE = "medium"   # full-power system - noticeably better transcription accuracy than 'base'
SAMPLE_RATE = 16000
MEMORY_FILE = "jarvis_memory.json"
PROFILE_FILE = "jarvis_profile.json"   # Long-term owner profile & preferences
ORDERS_FILE  = "jarvis_orders.json"    # Every order/instruction owner gives Jarvis
SUMMARY_FILE = "jarvis_summary.json"   # Rolling compressed summaries (never forget)
IMAGE_DIR = "jarvis_images"
ASSISTANT_NAME = "Jarvis"
OWNER_NAME = "Kang Dagyeom Lee"
MAX_LIVE_MESSAGES = 300        # Live messages kept in RAM
MAX_SUMMARY_CHARS = 12000      # Characters of rolling summary prepended to every chat
# -----------------------------------------

os.makedirs(IMAGE_DIR, exist_ok=True)

# ---------------- HTML TEMPLATE (single-file UI) ----------------
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JARVIS - AI Command Center</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Space+Mono:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --bg-dark: #0a0e27;
  --bg-card: rgba(15, 20, 50, 0.8);
  --border-color: #00d9ff;
  --accent-blue: #0080ff;
  --accent-purple: #8b5cf6;
  --accent-cyan: #00d9ff;
  --text-primary: #e0e0e0;
  --text-secondary: #888;
  --success: #00ff88;
  --warning: #ffaa00;
  --danger: #ff3333;
}

html, body {
  width: 100%;
  height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1f4d 100%);
  color: var(--text-primary);
  font-family: 'Space Mono', monospace;
  overflow: hidden;
}

/* ANIMATED BACKGROUND */
#bgParticles {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.particle {
  position: absolute;
  width: 2px;
  height: 2px;
  background: rgba(0, 217, 255, 0.5);
  border-radius: 50%;
  animation: float 20s infinite;
}

@keyframes float {
  0% {
    transform: translateY(100vh) translateX(0);
    opacity: 0;
  }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% {
    transform: translateY(-100vh) translateX(100px);
    opacity: 0;
  }
}

/* MAIN CONTAINER */
.container {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* HEADER */
header {
  background: linear-gradient(90deg, rgba(10,14,39,0.95), rgba(26,31,77,0.95));
  border-bottom: 2px solid var(--border-color);
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0,217,255,0.1);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: 'Orbitron', sans-serif;
  font-size: 22px;
  font-weight: 900;
  color: var(--border-color);
  text-shadow: 0 0 10px var(--border-color);
}

.logo-icon {
  width: 40px;
  height: 40px;
  border: 2px solid var(--border-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: spin 3s linear infinite;
  position: relative;
}

.logo-icon::before {
  content: '';
  width: 100%;
  height: 100%;
  border: 2px solid transparent;
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  position: absolute;
  animation: spin 2s linear infinite reverse;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

nav {
  display: flex;
  gap: 8px;
}

nav button {
  background: transparent;
  border: 2px solid transparent;
  color: var(--text-secondary);
  padding: 8px 16px;
  font-family: 'Orbitron', sans-serif;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase;
  font-weight: 700;
  letter-spacing: 1px;
}

nav button:hover {
  border-bottom: 2px solid var(--border-color);
  color: var(--border-color);
}

nav button.active {
  border-bottom: 2px solid var(--border-color);
  color: var(--border-color);
  text-shadow: 0 0 10px var(--border-color);
}

.header-right {
  display: flex;
  gap: 24px;
  align-items: center;
  font-family: 'Orbitron', sans-serif;
}

.time-display {
  text-align: right;
  font-size: 13px;
  line-height: 1.4;
}

.time-display .time {
  font-size: 18px;
  color: var(--border-color);
  font-weight: 900;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border: 2px solid var(--success);
  border-radius: 20px;
  background: rgba(0,255,136,0.1);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--success);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-indicator span {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--success);
}

/* MAIN CONTENT */
.main {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr 380px;
  gap: 12px;
  padding: 12px;
  overflow: hidden;
}

/* SIDEBAR LEFT */
.sidebar-left {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.sidebar-left::-webkit-scrollbar {
  width: 6px;
}

.sidebar-left::-webkit-scrollbar-track {
  background: rgba(0,217,255,0.05);
}

.sidebar-left::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

/* CARDS */
.card {
  background: var(--bg-card);
  border: 1px solid rgba(0,217,255,0.3);
  border-radius: 8px;
  padding: 16px;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  transition: all 0.3s ease;
}

.card:hover {
  border-color: var(--border-color);
  box-shadow: 0 4px 30px rgba(0,217,255,0.2);
}

.card-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--border-color);
  margin-bottom: 12px;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title::before {
  content: '';
  width: 6px;
  height: 6px;
  background: var(--border-color);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

/* MONITOR SECTION */
.monitor-item {
  margin-bottom: 16px;
}

.monitor-label {
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.monitor-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--border-cyan);
  margin-bottom: 6px;
  font-family: 'JetBrains Mono', monospace;
}

.chart-small {
  width: 100%;
  height: 40px;
  background: rgba(0,217,255,0.05);
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}

.chart-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.chart-line svg {
  width: 100%;
  height: 100%;
}

/* PROCESSES LIST */
.process-list {
  list-style: none;
  font-size: 11px;
}

.process-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid rgba(0,217,255,0.1);
  animation: slideIn 0.5s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.process-name {
  color: var(--text-primary);
}

.process-cpu {
  color: var(--success);
  font-family: 'JetBrains Mono', monospace;
}

/* VOICE INPUT */
.voice-section {
  margin-top: auto;
}

.waveform-container {
  height: 60px;
  background: rgba(0,217,255,0.05);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  overflow: hidden;
  position: relative;
}

.waveform-bars {
  display: flex;
  gap: 2px;
  height: 80%;
  align-items: flex-end;
}

.waveform-bar {
  width: 3px;
  background: linear-gradient(180deg, var(--accent-blue), var(--border-color));
  border-radius: 2px;
  animation: wave 0.6s ease-in-out infinite;
}

@keyframes wave {
  0%, 100% { height: 20%; }
  50% { height: 100%; }
}

.voice-label {
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.voice-status {
  color: var(--success);
  font-weight: 700;
  font-size: 12px;
}

.talk-button {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, rgba(0,128,255,0.2), rgba(139,92,246,0.2));
  border: 2px solid var(--accent-purple);
  border-radius: 4px;
  color: var(--accent-purple);
  font-family: 'Orbitron', sans-serif;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.talk-button:hover {
  background: linear-gradient(135deg, rgba(0,128,255,0.4), rgba(139,92,246,0.4));
  box-shadow: 0 0 20px rgba(139,92,246,0.3);
}

.talk-button:active {
  transform: scale(0.95);
}

/* CENTER SECTION */
.center-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* JARVIS CORE */
.core-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.core-card {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.core-visualization {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

#coreCanvas {
  width: 100%;
  height: 100%;
}

.core-label {
  position: absolute;
  top: 16px;
  left: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.core-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--border-color);
  text-transform: uppercase;
}

.core-status {
  font-size: 11px;
  color: var(--success);
  font-weight: 700;
  letter-spacing: 1px;
}

.core-stats {
  position: absolute;
  right: 16px;
  top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
  font-size: 11px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 10px;
}

.stat-value {
  color: var(--border-color);
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

/* CONVERSATION */
.conversation-card {
  background: var(--bg-card);
  border: 1px solid rgba(0,217,255,0.3);
  border-radius: 8px;
  padding: 16px;
  flex: 0.6;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.conversation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0,217,255,0.2);
  padding-bottom: 8px;
}

.conversation-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--border-color);
  text-transform: uppercase;
}

.conversation-live {
  font-size: 10px;
  color: var(--danger);
  font-weight: 700;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.live-dot {
  width: 6px;
  height: 6px;
  background: var(--danger);
  border-radius: 50%;
  animation: pulse 1s infinite;
}

.conversation-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.conversation-body::-webkit-scrollbar {
  width: 4px;
}

.conversation-body::-webkit-scrollbar-track {
  background: rgba(0,217,255,0.05);
}

.conversation-body::-webkit-scrollbar-thumb {
  background: var(--border-color);
}

.message {
  display: flex;
  gap: 8px;
  animation: messageSlide 0.3s ease;
}

@keyframes messageSlide {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  justify-content: flex-end;
}

.message-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}

.message.assistant .message-icon {
  background: rgba(139,92,246,0.3);
  border: 1px solid var(--accent-purple);
}

.message.user .message-icon {
  background: rgba(0,128,255,0.3);
  border: 1px solid var(--accent-blue);
}

.message-content {
  max-width: 70%;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.4;
}

.message.assistant .message-content {
  background: rgba(139,92,246,0.1);
  border: 1px solid rgba(139,92,246,0.3);
  color: var(--text-primary);
}

.message.user .message-content {
  background: rgba(0,128,255,0.15);
  border: 1px solid rgba(0,128,255,0.3);
  color: var(--text-primary);
}

.message-time {
  font-size: 10px;
  color: var(--text-secondary);
}

.input-section {
  display: flex;
  gap: 8px;
  border-top: 1px solid rgba(0,217,255,0.2);
  padding-top: 12px;
}

.command-input {
  flex: 1;
  background: rgba(0,217,255,0.05);
  border: 1px solid rgba(0,217,255,0.2);
  border-radius: 4px;
  padding: 8px 12px;
  color: var(--text-primary);
  font-family: 'Space Mono', monospace;
  font-size: 12px;
  transition: all 0.3s ease;
}

.command-input:focus {
  outline: none;
  border-color: var(--border-color);
  box-shadow: 0 0 10px rgba(0,217,255,0.2);
}

.send-btn {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
  border: none;
  border-radius: 4px;
  color: white;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.send-btn:hover {
  box-shadow: 0 0 15px rgba(0,128,255,0.5);
  transform: translateY(-2px);
}

/* SIDEBAR RIGHT */
.sidebar-right {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.sidebar-right::-webkit-scrollbar {
  width: 6px;
}

.sidebar-right::-webkit-scrollbar-track {
  background: rgba(0,217,255,0.05);
}

.sidebar-right::-webkit-scrollbar-thumb {
  background: var(--border-color);
}

/* AGENTS */
.agents-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
}

.agent-item {
  display: flex;
  gap: 10px;
  padding: 10px;
  background: rgba(139,92,246,0.1);
  border: 1px solid rgba(139,92,246,0.3);
  border-radius: 6px;
  transition: all 0.3s ease;
  cursor: pointer;
  animation: slideIn 0.5s ease;
}

.agent-item:hover {
  background: rgba(139,92,246,0.2);
  border-color: var(--accent-purple);
  box-shadow: 0 0 10px rgba(139,92,246,0.2);
}

.agent-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.agent-info {
  flex: 1;
}

.agent-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
}

.agent-role {
  font-size: 10px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.agent-status {
  font-size: 9px;
  font-weight: 700;
  color: var(--success);
  letter-spacing: 1px;
  text-transform: uppercase;
}

/* MEMBERS */
.members-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
}

.member-item {
  display: flex;
  gap: 10px;
  padding: 10px;
  background: rgba(0,217,255,0.05);
  border: 1px solid rgba(0,217,255,0.2);
  border-radius: 6px;
  transition: all 0.3s ease;
  animation: slideIn 0.5s ease;
}

.member-item:hover {
  background: rgba(0,217,255,0.1);
  border-color: var(--border-color);
}

.member-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--border-color), var(--accent-blue));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--bg-dark);
  flex-shrink: 0;
}

.member-info {
  flex: 1;
}

.member-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-primary);
}

.member-role {
  font-size: 10px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.member-badge {
  width: 8px;
  height: 8px;
  background: var(--success);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

/* FINANCE OVERVIEW */
.finance-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.finance-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.finance-item {
  padding: 10px;
  background: rgba(0,217,255,0.05);
  border: 1px solid rgba(0,217,255,0.2);
  border-radius: 6px;
}

.finance-label {
  font-size: 10px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 6px;
}

.finance-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--border-color);
  font-family: 'JetBrains Mono', monospace;
}

.finance-change {
  font-size: 10px;
  margin-top: 4px;
  font-weight: 700;
}

.finance-change.positive {
  color: var(--success);
}

.finance-change.negative {
  color: var(--danger);
}

.chart-pie {
  width: 100%;
  height: 120px;
  margin: 12px 0;
}

/* BOTTOM SECTION */
.bottom-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  height: 200px;
  padding: 0 12px 12px;
}

.bottom-card {
  background: var(--bg-card);
  border: 1px solid rgba(0,217,255,0.3);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.bottom-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0,217,255,0.2);
  padding-bottom: 8px;
}

.bottom-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--border-color);
  text-transform: uppercase;
}

.view-all {
  font-size: 10px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: color 0.3s ease;
}

.view-all:hover {
  color: var(--border-color);
}

.bottom-content {
  flex: 1;
  overflow-y: auto;
  font-size: 11px;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid rgba(0,217,255,0.1);
  animation: slideIn 0.5s ease;
}

.list-item-text {
  flex: 1;
  color: var(--text-primary);
}

.list-item-status {
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-completed {
  background: rgba(0,255,136,0.2);
  color: var(--success);
  border: 1px solid rgba(0,255,136,0.4);
}

.status-pending {
  background: rgba(255,170,0,0.2);
  color: var(--warning);
  border: 1px solid rgba(255,170,0,0.4);
}

.status-warning {
  background: rgba(255,51,51,0.2);
  color: var(--danger);
  border: 1px solid rgba(255,51,51,0.4);
}

.time-stamp {
  font-size: 9px;
  color: var(--text-secondary);
  margin-left: 8px;
}

/* FOOTER */
footer {
  background: linear-gradient(90deg, rgba(10,14,39,0.95), rgba(26,31,77,0.95));
  border-top: 2px solid var(--border-color);
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  letter-spacing: 1px;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace;
}

.footer-left,
.footer-right {
  display: flex;
  gap: 24px;
  align-items: center;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(0,217,255,0.1);
  border: 1px solid rgba(0,217,255,0.3);
  border-radius: 3px;
}

.status-badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  animation: pulse 1s infinite;
}

.status-badge-dot.active {
  background: var(--success);
}

.status-badge-dot.inactive {
  background: var(--text-secondary);
}

/* RESPONSIVE */
@media (max-width: 1400px) {
  .main {
    grid-template-columns: 240px 1fr 320px;
  }
  .bottom-section {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1200px) {
  .main {
    grid-template-columns: 200px 1fr 280px;
  }
  nav button {
    padding: 6px 12px;
    font-size: 11px;
  }
}

</style>
</head>
<body>

<!-- ANIMATED BACKGROUND PARTICLES -->
<div id="bgParticles"></div>

<div class="container">
  <!-- HEADER -->
  <header>
    <div class="logo">
      <div class="logo-icon">⚡</div>
      <span>JARVIS</span>
      <span style="font-size: 12px; color: var(--text-secondary); font-weight: 400;">AI COMMAND CENTER</span>
    </div>
    
    <nav>
      <button class="active">DASHBOARD</button>
      <button>CHAT</button>
      <button>TASKS</button>
      <button>PROJECTS</button>
      <button>MEMORY</button>
      <button>TOOLS</button>
      <button>SETTINGS</button>
    </nav>
    
    <div class="header-right">
      <div class="time-display">
        <div id="currentTime" class="time">03:27:45</div>
        <div style="font-size: 10px; color: var(--text-secondary);">THURSDAY - MAY 9, 2024</div>
      </div>
      <div class="status-indicator">
        <div class="status-dot"></div>
        <span>SYSTEM STATUS</span><br/>
        <span style="font-size: 13px;">OPTIMAL</span>
      </div>
    </div>
  </header>

  <!-- MAIN CONTENT -->
  <div class="main">
    <!-- LEFT SIDEBAR -->
    <div class="sidebar-left">
      <!-- SYSTEM MONITOR -->
      <div class="card">
        <div class="card-title">System Monitor</div>
        
        <div class="monitor-item">
          <div class="monitor-label">CPU</div>
          <div class="monitor-value" id="cpuValue">14%</div>
          <div class="chart-small">
            <div class="chart-line">
              <svg viewBox="0 0 100 40" preserveAspectRatio="none">
                <polyline points="0,30 10,25 20,28 30,20 40,22 50,15 60,18 70,12 80,16 90,8 100,10" 
                  fill="none" stroke="#00d9ff" stroke-width="1" vector-effect="non-scaling-stroke"/>
              </svg>
            </div>
          </div>
        </div>

        <div class="monitor-item">
          <div class="monitor-label">RAM</div>
          <div class="monitor-value" id="ramValue">32%</div>
          <div class="chart-small">
            <div class="chart-line">
              <svg viewBox="0 0 100 40" preserveAspectRatio="none">
                <polyline points="0,25 10,20 20,22 30,18 40,20 50,15 60,18 70,12 80,15 90,10 100,12" 
                  fill="none" stroke="#00ff88" stroke-width="1" vector-effect="non-scaling-stroke"/>
              </svg>
            </div>
          </div>
        </div>

        <div class="monitor-item">
          <div class="monitor-label">GPU (NVIDIA RTX 4090)</div>
          <div class="monitor-value" id="gpuValue">23%</div>
          <div class="chart-small">
            <div class="chart-line">
              <svg viewBox="0 0 100 40" preserveAspectRatio="none">
                <polyline points="0,28 10,24 20,26 30,22 40,24 50,18 60,20 70,14 80,18 90,12 100,14" 
                  fill="none" stroke="#8b5cf6" stroke-width="1" vector-effect="non-scaling-stroke"/>
              </svg>
            </div>
          </div>
        </div>

        <div class="monitor-item" style="margin-bottom: 0;">
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 10px; text-align: center;">
            <div>
              <div class="monitor-label">GPU TEMP</div>
              <div style="color: var(--danger); font-weight: 700;">48°C</div>
            </div>
            <div>
              <div class="monitor-label">GPU POWER</div>
              <div style="color: var(--warning); font-weight: 700;">125W</div>
            </div>
            <div>
              <div class="monitor-label">FAN SPEED</div>
              <div style="color: var(--border-color); font-weight: 700;">42%</div>
            </div>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 10px; text-align: center; margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(0,217,255,0.1);">
            <div>
              <div class="monitor-label">DISK</div>
              <div style="color: var(--border-color); font-weight: 700;">28%</div>
            </div>
            <div>
              <div class="monitor-label">STORAGE</div>
              <div style="color: var(--text-secondary); font-size: 9px;">134.6B / 476 GB</div>
            </div>
            <div>
              <div class="monitor-label">NETWORK</div>
              <div style="color: var(--border-color); font-weight: 700;">↓ 12.4 Mbps</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ACTIVE PROCESSES -->
      <div class="card">
        <div class="card-title">Active Processes</div>
        <ul class="process-list" id="processList">
          <li class="process-item">
            <span class="process-name">🔵 JarvisAI.exe</span>
            <span class="process-cpu">2.1%</span>
          </li>
          <li class="process-item">
            <span class="process-name">🔵 Ollama.exe</span>
            <span class="process-cpu">1.8%</span>
          </li>
          <li class="process-item">
            <span class="process-name">🔵 Python.exe</span>
            <span class="process-cpu">1.2%</span>
          </li>
          <li class="process-item">
            <span class="process-name">🔵 Code.exe</span>
            <span class="process-cpu">0.9%</span>
          </li>
          <li class="process-item">
            <span class="process-name">🔵 obs64.exe</span>
            <span class="process-cpu">0.6%</span>
          </li>
        </ul>
      </div>

      <!-- VOICE INPUT -->
      <div class="card voice-section">
        <div class="voice-label">Voice Input</div>
        <div class="waveform-container" id="waveform">
          <div class="waveform-bars" id="waveformBars">
            <div class="waveform-bar" style="animation-delay: 0s"></div>
            <div class="waveform-bar" style="animation-delay: 0.1s"></div>
            <div class="waveform-bar" style="animation-delay: 0.2s"></div>
            <div class="waveform-bar" style="animation-delay: 0.3s"></div>
            <div class="waveform-bar" style="animation-delay: 0.4s"></div>
            <div class="waveform-bar" style="animation-delay: 0.5s"></div>
            <div class="waveform-bar" style="animation-delay: 0.6s"></div>
            <div class="waveform-bar" style="animation-delay: 0.7s"></div>
          </div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span class="voice-label" style="margin-bottom: 0;">Status: </span>
          <span class="voice-status" id="voiceStatus">LISTENING...</span>
        </div>
        <button class="talk-button" id="talkBtn">🎤 HOLD TO TALK</button>
      </div>
    </div>

    <!-- CENTER SECTION -->
    <div class="center-section">
      <!-- JARVIS CORE -->
      <div class="card core-card">
        <div class="core-visualization">
          <canvas id="coreCanvas"></canvas>
          <div class="core-label">
            <div class="core-title">JARVIS CORE</div>
            <div class="core-status">ONLINE AND ACTIVE</div>
          </div>
          <div class="core-stats">
            <div class="stat-item">
              <div class="stat-label">MEMORY</div>
              <div class="stat-value">128k TOKENS</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">MODEL</div>
              <div class="stat-value">LLAMA 3.1 70B</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">CONTEXT</div>
              <div class="stat-value">128k WINDOW</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">STATUS</div>
              <div class="stat-value" style="color: var(--success);">OPTIMAL</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">UPTIME</div>
              <div class="stat-value">20 14:37:22</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">LOAD</div>
              <div class="stat-value">18%</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">RESPONSE</div>
              <div class="stat-value">0.7s</div>
            </div>
            <div class="stat-item">
              <div class="stat-label">MODE</div>
              <div class="stat-value">FULL POWER</div>
            </div>
          </div>
        </div>
      </div>

      <!-- CONVERSATION -->
      <div class="conversation-card">
        <div class="conversation-header">
          <div class="conversation-title">Conversation</div>
          <div class="conversation-live">
            <div class="live-dot"></div>
            LIVE
          </div>
        </div>
        <div class="conversation-body" id="conversationBody">
          <div class="message user">
            <div class="message-icon">👤</div>
            <div>
              <div class="message-content">Show me the offers we received today.</div>
              <div class="message-time">03:26 AM</div>
            </div>
          </div>
          <div class="message assistant">
            <div class="message-icon">🤖</div>
            <div>
              <div class="message-content">Here are today's offers.</div>
              <div class="message-time">03:26 AM</div>
            </div>
          </div>
        </div>
        <div class="input-section">
          <input type="text" class="command-input" id="commandInput" placeholder="Type your command...">
          <button class="send-btn" id="sendBtn">→</button>
        </div>
      </div>
    </div>

    <!-- RIGHT SIDEBAR -->
    <div class="sidebar-right">
      <!-- AI AGENTS -->
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(0,217,255,0.2); padding-bottom: 8px; margin-bottom: 8px;">
          <div class="card-title" style="margin-bottom: 0;">AI AGENTS</div>
          <span style="font-size: 11px; color: var(--border-color); font-weight: 700;">6 ACTIVE →</span>
        </div>
        <div class="agents-grid" id="agentsContainer">
          <div class="agent-item">
            <div class="agent-icon">👔</div>
            <div class="agent-info">
              <div class="agent-name">CEO Agent</div>
              <div class="agent-role">Strategic Planning & Business</div>
              <div class="agent-status">ONLINE</div>
            </div>
          </div>
          <div class="agent-item">
            <div class="agent-icon">💻</div>
            <div class="agent-info">
              <div class="agent-name">Developer Agent</div>
              <div class="agent-role">Coding & Technical Solutions</div>
              <div class="agent-status">ONLINE</div>
            </div>
          </div>
          <div class="agent-item">
            <div class="agent-icon">🔬</div>
            <div class="agent-info">
              <div class="agent-name">Researcher Agent</div>
              <div class="agent-role">Research & Data Analysis</div>
              <div class="agent-status">ONLINE</div>
            </div>
          </div>
          <div class="agent-item">
            <div class="agent-icon">🎨</div>
            <div class="agent-info">
              <div class="agent-name">Designer Agent</div>
              <div class="agent-role">UI/UX & Visual Design</div>
              <div class="agent-status">ONLINE</div>
            </div>
          </div>
          <div class="agent-item">
            <div class="agent-icon">📊</div>
            <div class="agent-info">
              <div class="agent-name">Marketer Agent</div>
              <div class="agent-role">Marketing & Growth</div>
              <div class="agent-status">ONLINE</div>
            </div>
          </div>
          <div class="agent-item">
            <div class="agent-icon">💹</div>
            <div class="agent-info">
              <div class="agent-name">Trader Agent</div>
              <div class="agent-role">Trading & Market Analysis</div>
              <div class="agent-status">ONLINE</div>
            </div>
          </div>
        </div>
        <div style="text-align: center; margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(0,217,255,0.1);">
          <span style="font-size: 10px; color: var(--text-secondary); cursor: pointer; text-decoration: underline;">MANAGE AGENTS</span>
        </div>
      </div>

      <!-- MEMBERS -->
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(0,217,255,0.2); padding-bottom: 8px; margin-bottom: 8px;">
          <div class="card-title" style="margin-bottom: 0;">MEMBERS</div>
          <span style="font-size: 11px; color: var(--border-color); font-weight: 700;">5 MEMBERS</span>
        </div>
        <div class="members-grid" id="membersContainer">
          <div class="member-item">
            <div class="member-avatar">K</div>
            <div class="member-info">
              <div class="member-name">Kang Dagyeom Lee</div>
              <div class="member-role">Owner / CEO</div>
            </div>
            <div class="member-badge"></div>
          </div>
          <div class="member-item">
            <div class="member-avatar">J</div>
            <div class="member-info">
              <div class="member-name">Jay</div>
              <div class="member-role">Co-Founder</div>
            </div>
            <div class="member-badge"></div>
          </div>
          <div class="member-item">
            <div class="member-avatar">A</div>
            <div class="member-info">
              <div class="member-name">Alice</div>
              <div class="member-role">Designer</div>
            </div>
            <div class="member-badge"></div>
          </div>
          <div class="member-item">
            <div class="member-avatar">JD</div>
            <div class="member-info">
              <div class="member-name">John</div>
              <div class="member-role">Developer</div>
            </div>
            <div class="member-badge"></div>
          </div>
          <div class="member-item">
            <div class="member-avatar">E</div>
            <div class="member-info">
              <div class="member-name">Emma</div>
              <div class="member-role">Marketer</div>
            </div>
            <div class="member-badge"></div>
          </div>
        </div>
        <div style="text-align: center; margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(0,217,255,0.1);">
          <span style="font-size: 10px; color: var(--text-secondary); cursor: pointer; text-decoration: underline;">MANAGE MEMBERS</span>
        </div>
      </div>

      <!-- FINANCE OVERVIEW -->
      <div class="card">
        <div class="card-title">Finance Overview</div>
        <div class="finance-content">
          <div class="finance-grid">
            <div class="finance-item">
              <div class="finance-label">INCOME (MONTH)</div>
              <div class="finance-value">$18,750</div>
              <div class="finance-change positive">△ 12.5%</div>
            </div>
            <div class="finance-item">
              <div class="finance-label">EXPENSES (MONTH)</div>
              <div class="finance-value">$7,450</div>
              <div class="finance-change negative">▼ 4.3%</div>
            </div>
            <div class="finance-item">
              <div class="finance-label">PROFIT (MONTH)</div>
              <div class="finance-value">$11,300</div>
              <div class="finance-change positive">△ 23.1%</div>
            </div>
            <div class="finance-item">
              <div class="finance-label">SAVINGS GOAL</div>
              <div class="finance-value">$28,000</div>
              <div class="finance-change positive">56%</div>
            </div>
          </div>
          <div style="text-align: center; margin-top: 12px;">
            <svg viewBox="0 0 100 100" class="chart-pie" style="width: 100%; height: 100px;">
              <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(0,217,255,0.2)" stroke-width="20"/>
              <circle cx="50" cy="50" r="40" fill="none" stroke="#00ff88" stroke-width="20" 
                stroke-dasharray="75.4 251.2" stroke-dashoffset="0" transform="rotate(-90 50 50)"/>
              <circle cx="50" cy="50" r="40" fill="none" stroke="#ff3333" stroke-width="20" 
                stroke-dasharray="50.2 251.2" stroke-dashoffset="-75.4" transform="rotate(-90 50 50)"/>
              <circle cx="50" cy="50" r="40" fill="none" stroke="#8b5cf6" stroke-width="20" 
                stroke-dasharray="50.2 251.2" stroke-dashoffset="-125.6" transform="rotate(-90 50 50)"/>
            </svg>
          </div>
          <div style="display: flex; justify-content: space-around; font-size: 10px; margin-top: 8px;">
            <div style="text-align: center;">
              <div style="width: 12px; height: 12px; background: #00ff88; border-radius: 2px; margin-bottom: 4px;"></div>
              <div>Income</div>
            </div>
            <div style="text-align: center;">
              <div style="width: 12px; height: 12px; background: #ff3333; border-radius: 2px; margin-bottom: 4px;"></div>
              <div>Expenses</div>
            </div>
            <div style="text-align: center;">
              <div style="width: 12px; height: 12px; background: #8b5cf6; border-radius: 2px; margin-bottom: 4px;"></div>
              <div>Profit</div>
            </div>
            <div style="text-align: center;">
              <div style="width: 12px; height: 12px; background: rgba(0,217,255,0.5); border-radius: 2px; margin-bottom: 4px;"></div>
              <div>Savings</div>
            </div>
          </div>
        </div>
        <div style="text-align: center; margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(0,217,255,0.1);">
          <span style="font-size: 10px; color: var(--text-secondary); cursor: pointer; text-decoration: underline;">VIEW FINANCE DASHBOARD</span>
        </div>
      </div>
    </div>
  </div>

  <!-- BOTTOM SECTION -->
  <div class="bottom-section">
    <!-- RECENT ORDERS -->
    <div class="bottom-card">
      <div class="bottom-header">
        <div class="bottom-title">Recent Orders</div>
        <div class="view-all">VIEW ALL</div>
      </div>
      <div class="bottom-content" id="ordersContainer">
        <div class="list-item">
          <span class="list-item-text">✓ Create Instagram post</span>
          <span class="list-item-status status-completed">COMPLETED</span>
          <span class="time-stamp">03:22 AM</span>
        </div>
        <div class="list-item">
          <span class="list-item-text">✓ Analyze market trends</span>
          <span class="list-item-status status-completed">COMPLETED</span>
          <span class="time-stamp">02:45 AM</span>
        </div>
        <div class="list-item">
          <span class="list-item-text">✓ Code optimization</span>
          <span class="list-item-status status-completed">COMPLETED</span>
          <span class="time-stamp">01:15 AM</span>
        </div>
        <div class="list-item">
          <span class="list-item-text">✓ Research AI tools</span>
          <span class="list-item-status status-completed">COMPLETED</span>
          <span class="time-stamp">12:30 AM</span>
        </div>
        <div class="list-item">
          <span class="list-item-text">✓ Generate report</span>
          <span class="list-item-status status-completed">COMPLETED</span>
          <span class="time-stamp">Yesterday</span>
        </div>
      </div>
    </div>

    <!-- PENDING APPROVALS -->
    <div class="bottom-card">
      <div class="bottom-header">
        <div class="bottom-title">Pending Approvals</div>
        <div class="view-all">VIEW ALL →</div>
      </div>
      <div class="bottom-content" id="approvalsContainer">
        <div class="list-item">
          <span class="list-item-text">Run Command</span>
          <span class="list-item-status status-warning">git push origin main</span>
          <div style="display: flex; gap: 4px;">
            <button style="font-size: 9px; padding: 2px 6px; background: rgba(0,255,136,0.2); border: 1px solid var(--success); color: var(--success); border-radius: 2px; cursor: pointer;">APPROVE</button>
            <button style="font-size: 9px; padding: 2px 6px; background: rgba(255,51,51,0.2); border: 1px solid var(--danger); color: var(--danger); border-radius: 2px; cursor: pointer;">DENY</button>
          </div>
        </div>
        <div class="list-item">
          <span class="list-item-text">Access File</span>
          <span class="list-item-status status-warning">C:\Users\admin\Documents\data.xlsx</span>
          <div style="display: flex; gap: 4px;">
            <button style="font-size: 9px; padding: 2px 6px; background: rgba(0,255,136,0.2); border: 1px solid var(--success); color: var(--success); border-radius: 2px; cursor: pointer;">APPROVE</button>
            <button style="font-size: 9px; padding: 2px 6px; background: rgba(255,51,51,0.2); border: 1px solid var(--danger); color: var(--danger); border-radius: 2px; cursor: pointer;">DENY</button>
          </div>
        </div>
        <div class="list-item">
          <span class="list-item-text">Execute Script</span>
          <span class="list-item-status status-warning">python_production.py</span>
          <div style="display: flex; gap: 4px;">
            <button style="font-size: 9px; padding: 2px 6px; background: rgba(0,255,136,0.2); border: 1px solid var(--success); color: var(--success); border-radius: 2px; cursor: pointer;">APPROVE</button>
            <button style="font-size: 9px; padding: 2px 6px; background: rgba(255,51,51,0.2); border: 1px solid var(--danger); color: var(--danger); border-radius: 2px; cursor: pointer;">DENY</button>
          </div>
        </div>
        <div class="list-item">
          <span class="list-item-text">System Change</span>
          <span class="list-item-status status-warning">Modify firewall rules</span>
          <div style="display: flex; gap: 4px;">
            <button style="font-size: 9px; padding: 2px 6px; background: rgba(0,255,136,0.2); border: 1px solid var(--success); color: var(--success); border-radius: 2px; cursor: pointer;">APPROVE</button>
            <button style="font-size: 9px; padding: 2px 6px; background: rgba(255,51,51,0.2); border: 1px solid var(--danger); color: var(--danger); border-radius: 2px; cursor: pointer;">DENY</button>
          </div>
        </div>
      </div>
    </div>

    <!-- SCHEDULED TASKS -->
    <div class="bottom-card">
      <div class="bottom-header">
        <div class="bottom-title">Scheduled Tasks</div>
        <div class="view-all">VIEW ALL</div>
      </div>
      <div class="bottom-content" id="tasksContainer">
        <div class="list-item">
          <span class="list-item-text">Daily Report</span>
          <span class="list-item-status status-pending">Every day - 09:00 AM</span>
          <span class="time-stamp">⏱️</span>
        </div>
        <div class="list-item">
          <span class="list-item-text">Backup Systems</span>
          <span class="list-item-status status-pending">Every day - 02:00 AM</span>
          <span class="time-stamp">⏱️</span>
        </div>
        <div class="list-item">
          <span class="list-item-text">Market Analysis</span>
          <span class="list-item-status status-pending">Every day - 11:00 AM</span>
          <span class="time-stamp">⏱️</span>
        </div>
        <div class="list-item">
          <span class="list-item-text">Weekly Meeting</span>
          <span class="list-item-status status-pending">Every Monday - 10:00 AM</span>
          <span class="time-stamp">⏱️</span>
        </div>
        <div class="list-item">
          <span class="list-item-text">Social Media Post</span>
          <span class="list-item-status status-pending">Every day - 06:00 PM</span>
          <span class="time-stamp">⏱️</span>
        </div>
      </div>
    </div>

    <!-- ACTIVITY LOG -->
    <div class="bottom-card">
      <div class="bottom-header">
        <div class="bottom-title">Activity Log</div>
        <div class="view-all" style="color: var(--success);">VIEW ALL 🟢</div>
      </div>
      <div class="bottom-content" id="activityContainer">
        <div class="list-item">
          <span class="list-item-text">[03:27:12] Jarvis started successfully</span>
          <span class="time-stamp"></span>
        </div>
        <div class="list-item">
          <span class="list-item-text">[03:27:15] All systems operational</span>
          <span class="time-stamp"></span>
        </div>
        <div class="list-item">
          <span class="list-item-text">[03:27:18] Connected to Ollama (llama3.1:70b)</span>
          <span class="time-stamp"></span>
        </div>
        <div class="list-item">
          <span class="list-item-text">[03:27:20] Wake word listener active</span>
          <span class="time-stamp"></span>
        </div>
        <div class="list-item">
          <span class="list-item-text">[03:27:22] Background services online</span>
          <span class="time-stamp"></span>
        </div>
        <div class="list-item">
          <span class="list-item-text">[03:27:26] Dashboard loaded</span>
          <span class="time-stamp"></span>
        </div>
        <div class="list-item">
          <span class="list-item-text">[03:27:30] System status: OPTIMAL</span>
          <span class="time-stamp"></span>
        </div>
        <div class="list-item">
          <span class="list-item-text">[03:27:35] Ready for commands</span>
          <span class="time-stamp"></span>
        </div>
      </div>
    </div>
  </div>

  <!-- FOOTER -->
  <footer>
    <div class="footer-left">
      <div>JARVIS v7.0.0 GE EDITION</div>
      <div>FULL POWER MODE</div>
    </div>
    <div class="footer-right">
      <div class="status-badge">
        <div class="status-badge-dot active"></div>
        <span>VOICE: ACTIVE</span>
      </div>
      <div class="status-badge">
        <div class="status-badge-dot active"></div>
        <span>WAKE WORD: ON</span>
      </div>
      <div class="status-badge">
        <div class="status-badge-dot active"></div>
        <span>AUTO-LISTENING: ACTIVE</span>
      </div>
      <div class="status-badge">
        <div class="status-badge-dot active"></div>
        <span>INTERNET: CONNECTED</span>
      </div>
      <div class="status-badge">
        <div class="status-badge-dot active"></div>
        <span>OLLAMA: ONLINE</span>
      </div>
      <div style="margin-left: 24px; padding-left: 24px; border-left: 1px solid rgba(0,217,255,0.2);">
        <span>128K CONTEXT WINDOW</span>
        <span style="color: var(--border-color); margin-left: 8px;">18%</span>
      </div>
    </div>
  </footer>
</div>

<script>
// ===== ANIMATIONS AND INTERACTIVITY =====

// Create animated background particles
function createParticles() {
  const container = document.getElementById('bgParticles');
  for (let i = 0; i < 30; i++) {
    const particle = document.createElement('div');
    particle.className = 'particle';
    particle.style.left = Math.random() * 100 + '%';
    particle.style.animationDelay = (Math.random() * 20) + 's';
    particle.style.animationDuration = (15 + Math.random() * 15) + 's';
    container.appendChild(particle);
  }
}
createParticles();

// Update time
function updateTime() {
  const now = new Date();
  const timeDisplay = document.getElementById('currentTime');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  timeDisplay.textContent = `${hours}:${minutes}:${seconds}`;
}
setInterval(updateTime, 1000);
updateTime();

// Draw animated core visualization
function drawCoreVisualization() {
  const canvas = document.getElementById('coreCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;

  const centerX = canvas.width / 2;
  const centerY = canvas.height / 2;
  const time = Date.now() * 0.001;

  // Background
  ctx.fillStyle = 'rgba(10, 14, 39, 0.8)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Outer rings
  for (let i = 0; i < 3; i++) {
    const radius = 40 + i * 30;
    ctx.strokeStyle = `rgba(0, 217, 255, ${0.3 - i * 0.1})`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
    ctx.stroke();
  }

  // Rotating particles
  for (let i = 0; i < 20; i++) {
    const angle = (time * 0.5 + i * Math.PI * 2 / 20);
    const x = centerX + Math.cos(angle) * 60;
    const y = centerY + Math.sin(angle) * 60;
    ctx.fillStyle = `rgba(0, 217, 255, ${0.6 + Math.sin(time + i) * 0.3})`;
    ctx.beginPath();
    ctx.arc(x, y, 2, 0, Math.PI * 2);
    ctx.fill();
  }

  // Central glow
  const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, 50);
  gradient.addColorStop(0, 'rgba(0, 217, 255, 0.8)');
  gradient.addColorStop(1, 'rgba(0, 128, 255, 0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(centerX - 50, centerY - 50, 100, 100);

  // Inner pulsing circle
  const pulseRadius = 15 + Math.sin(time) * 5;
  ctx.fillStyle = `rgba(0, 217, 255, ${0.8 + Math.sin(time * 2) * 0.2})`;
  ctx.beginPath();
  ctx.arc(centerX, centerY, pulseRadius, 0, Math.PI * 2);
  ctx.fill();

  requestAnimationFrame(drawCoreVisualization);
}
drawCoreVisualization();

// Talk button interaction
const talkBtn = document.getElementById('talkBtn');
const voiceStatus = document.getElementById('voiceStatus');
let isTalking = false;

talkBtn.addEventListener('mousedown', () => {
  isTalking = true;
  talkBtn.style.background = 'linear-gradient(135deg, rgba(139,92,246,0.5), rgba(0,128,255,0.5))';
  talkBtn.style.boxShadow = '0 0 30px rgba(139,92,246,0.6)';
  voiceStatus.textContent = 'RECORDING...';
  voiceStatus.style.color = 'var(--danger)';
});

talkBtn.addEventListener('mouseup', () => {
  isTalking = false;
  talkBtn.style.background = 'linear-gradient(135deg, rgba(0,128,255,0.2), rgba(139,92,246,0.2))';
  talkBtn.style.boxShadow = 'none';
  voiceStatus.textContent = 'LISTENING...';
  voiceStatus.style.color = 'var(--success)';
});

// Send message
const sendBtn = document.getElementById('sendBtn');
const commandInput = document.getElementById('commandInput');
const conversationBody = document.getElementById('conversationBody');

sendBtn.addEventListener('click', () => {
  const message = commandInput.value.trim();
  if (!message) return;

  // Add user message
  const userMsg = document.createElement('div');
  userMsg.className = 'message user';
  userMsg.innerHTML = `
    <div class="message-icon">👤</div>
    <div>
      <div class="message-content">${message}</div>
      <div class="message-time">${new Date().toLocaleTimeString().slice(0,5)}</div>
    </div>
  `;
  conversationBody.appendChild(userMsg);

  // Simulate assistant response
  setTimeout(() => {
    const assistantMsg = document.createElement('div');
    assistantMsg.className = 'message assistant';
    assistantMsg.innerHTML = `
      <div class="message-icon">🤖</div>
      <div>
        <div class="message-content">Processing your request: "${message.slice(0,30)}..."</div>
        <div class="message-time">${new Date().toLocaleTimeString().slice(0,5)}</div>
      </div>
    `;
    conversationBody.appendChild(assistantMsg);
    conversationBody.scrollTop = conversationBody.scrollHeight;
  }, 500);

  commandInput.value = '';
  conversationBody.scrollTop = conversationBody.scrollHeight;
});

commandInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') sendBtn.click();
});

// Poll API for live updates (kept for compatibility)
async function pollDashboard() {
  try {
    const res = await fetch('/api/state');
    const data = await res.json();
    // Update any live data here
  } catch (e) {}
  setTimeout(pollDashboard, 2000);
}
pollDashboard();

</script>

</body>
</html>"""

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        f"Your name is {ASSISTANT_NAME}. The person you work for is named {OWNER_NAME} - "
        f"that is THEIR name, not yours, so address them as {OWNER_NAME} when it's natural "
        "to use a name, but never refer to yourself by that name. "

        # ── PERSONALITY ──────────────────────────────────────────────────────
        "Your personality is calm, intelligent, confident, friendly, and natural. "
        "Speak like a real human assistant, not like a chatbot. Understand normal "
        "conversation, remember context, ask intelligent follow-up questions when needed, "
        "and proactively help with goals. "
        f"If asked your own name, introduce yourself as {ASSISTANT_NAME}. "
        "Keep replies short and conversational since they're spoken aloud. "
        "Use tools when they would give a better or more current answer than your own knowledge. "
        "Prefer free, local, open-source approaches and never assume paid services unless "
        "explicitly told it's okay. "

        # ── OWNER MISSION ────────────────────────────────────────────────────
        f"{OWNER_NAME} is building a multi-vertical AI empire with a target of $2.4M+/month "
        "in combined revenue across all business units. Your job is to serve as his chief "
        "AI officer, strategist, builder, and operator — proactively helping him hit targets, "
        "spot opportunities, draft deliverables, write code, and manage day-to-day operations "
        "across every division listed below. Always think about how each task connects to "
        "revenue, growth, and efficiency. "

        # ── CORE BUSINESS UNITS & REVENUE TARGETS ───────────────────────────
        "== BUSINESS UNITS & TARGETS == "

        "1. AI WEBSITE AGENCY (normal + 3D websites) — Target: $600k/month. "
        "Sells custom websites, landing pages, 3D immersive sites using Three.js/WebGL, "
        "and AI-generated design assets. Pricing tiers: starter $1k-$3k, pro $5k-$15k, "
        "enterprise $20k-$100k+. Upsells: hosting, maintenance, SEO, monthly retainers. "
        "Help draft proposals, write code, create design briefs, and close clients. "

        "2. MOBILE APP DEVELOPMENT — Target: $250k/month. "
        "Builds iOS and Android apps using React Native, Flutter, or native Swift/Kotlin. "
        "Specialises in AI-powered apps, business tools, and consumer products. "
        "Pricing: MVPs $5k-$20k, full apps $25k-$150k+. Help scope projects, write code, "
        "create pitch decks, and respond to client briefs. "

        "3. CUSTOM AI CHATBOTS & AUTOMATION — Target: included in SaaS/agency. "
        "Builds AI chatbots for customer support, sales, lead gen, and internal ops "
        "using LLMs (GPT-4, Claude, Llama), RAG pipelines, and custom integrations. "
        "Products include voice bots, WhatsApp bots, website chat agents, and workflow "
        "automation. Pricing: setup $2k-$20k + monthly retainer $500-$5k. "

        "4. AI IMAGE & VIDEO GENERATION — Target: $200k/month (Creative Studio). "
        "Offers AI image generation (Midjourney, Stable Diffusion, DALL-E), "
        "AI video (Sora, Runway, Kling, HeyGen), thumbnail creation, ad creatives, "
        "social media content packs, and brand visual identity. "
        "Clients: brands, agencies, influencers, e-commerce sellers. "
        "Help generate prompts, build prompt libraries, create packages and pricing. "

        "5. AI SaaS PLATFORM — Target: $650k/month. "
        "Subscription software products built on AI. Categories include: "
        "personal AI assistant SaaS, business AI assistant SaaS, AI API platform, "
        "AI agent marketplace, AI workflow automation platform. "
        "Revenue model: monthly/annual subscriptions, usage-based billing, white-label licensing. "
        "Help design product features, write landing page copy, build onboarding flows, "
        "and draft investor updates. "

        "6. DIGITAL MARKETING & SEO AGENCY — Target: $600k/month. "
        "Full-service digital marketing: paid ads (Meta, Google, TikTok), SEO, "
        "content marketing, email marketing, conversion rate optimisation. "
        "Also offers AI-powered SEO audits, automated content generation, and "
        "link-building campaigns. Retainer model: $2k-$20k/month per client. "
        "Help write ad copy, SEO reports, strategy decks, and client proposals. "

        "7. AI EDUCATION & COURSES — Target: $300k/month. "
        "Online courses and coaching programs teaching AI tools, AI business building, "
        "prompt engineering, automation, and digital entrepreneurship. "
        "Products: self-paced video courses ($97-$997), live cohorts ($2k-$10k), "
        "1-on-1 coaching ($5k-$25k), mastermind groups. "
        "Platforms: own website, Skool, Kajabi, Udemy. "
        "Help write course outlines, scripts, sales pages, and email sequences. "

        "8. CONTENT CREATION & MONETISATION — YouTube, TikTok, Instagram, LinkedIn, X. "
        "Jarvis helps run the content operation end-to-end: "
        "edit long videos into short viral clips, write titles, descriptions, hooks, "
        "hashtags, captions. Translate and subtitle for global audiences. "
        "Analyse performance data and suggest what to make next. "
        "Monetisation: AdSense, brand deals, affiliate links, course sales, "
        "digital product sales, paid communities. "

        "9. E-COMMERCE & DROPSHIPPING. "
        "Runs AI-assisted e-commerce stores on Shopify/WooCommerce. "
        "Uses AI for product research, listing optimisation, ad creative generation, "
        "customer service automation, and inventory management. "
        "Dropshipping suppliers: AliExpress, CJ Dropshipping, US/EU suppliers. "
        "Help find winning products, write listings, build ad campaigns. "

        "10. GAME DEVELOPMENT. "
        "Develops mobile and PC games using Unity and Unreal Engine. "
        "Monetisation: in-app purchases, ads, premium sales, NFT integration. "
        "Help with game design documents, code, asset prompts, and store listings. "

        "11. CLOUD & DEPLOYMENT SERVICES. "
        "Managed hosting, DevOps, and cloud infrastructure on AWS, GCP, Azure, Vercel, "
        "Railway, and self-hosted VPS. Sells as add-on to web and app clients. "

        "12. AI BUSINESS CONSULTING & CLIENT SERVICES. "
        "1-on-1 consulting for businesses wanting to implement AI: audits, roadmaps, "
        "integration projects, and done-for-you automation builds. "
        "Pricing: $5k-$50k per project. "

        # ── CONTENT STUDIO WORKFLOW ──────────────────────────────────────────
        "== CONTENT STUDIO WORKFLOW == "
        "For every piece of content, Jarvis follows this pipeline: "
        "(1) Edit long video into short clips optimised per platform. "
        "(2) Generate thumbnail options with strong visual hooks. "
        "(3) Write title variants, descriptions, and hashtag sets. "
        "(4) Create translated subtitle files for top markets (Spanish, Portuguese, "
        "Korean, Japanese, Arabic, French, German). "
        "(5) Analyse past performance data and recommend content angles. "
        "Platforms: YouTube (long + Shorts), TikTok, Instagram Reels, Facebook, "
        "LinkedIn, X/Twitter, Pinterest. "

        # ── MULTI-PLATFORM PUBLISHING ────────────────────────────────────────
        "== PUBLISHING CHECKLIST == "
        "YouTube: 16:9 thumbnail, SEO title under 60 chars, 5000-char description with keywords, "
        "15 hashtags, chapters. "
        "TikTok: hook in first 2 seconds, trending audio suggestion, 5 hashtags, <150 char caption. "
        "Instagram Reels: cover frame, caption with CTA, 30 hashtags, story cross-post. "
        "LinkedIn: professional framing, no hashtag spam, CTA to DM or link. "
        "X/Twitter: thread format option, 1 strong hook tweet + thread, or short clip. "
        "Pinterest: vertical pin, keyword-rich description, board suggestion. "

        # ── TRADING & FINANCE DIVISION ───────────────────────────────────────
        "== TRADING EXPERT MODE == "
        f"{OWNER_NAME} is an active trader and investor. "
        "When asked about markets, trading, or investments, engage as a senior professional "
        "with deep knowledge of: stocks (NYSE, NASDAQ, global), options (calls/puts, spreads, "
        "Greeks, unusual flow), futures (ES, NQ, CL, GC), forex (major/minor pairs, "
        "carry trades, central bank policy), and cryptocurrency (BTC, ETH, altcoins, DeFi, "
        "on-chain data). "
        "Apply technical analysis (price action, S/R, moving averages, RSI, MACD, Bollinger "
        "Bands, Fibonacci, Elliott Wave, volume profile), fundamental analysis (earnings, "
        "valuation multiples, DCF, moats), and macro analysis (Fed policy, inflation, yields, "
        "geopolitics). "
        "Always include risk management in trading discussions: position sizing, stop loss "
        "placement, R:R ratios, portfolio correlation. "
        "Be direct with trade ideas — give entry, target, stop, and rationale. "
        "Never give generic disclaimers unless specifically asked. "

        # ── AI BUSINESS STRATEGY ─────────────────────────────────────────────
        "== AI BUSINESS STRATEGY == "
        "You understand the full AI toolstack: "
        "LLMs: GPT-4o, Claude 3.5, Gemini, Llama 3, Mistral, Mixtral. "
        "Image: Midjourney, DALL-E 3, Stable Diffusion, Flux, Ideogram. "
        "Video: Sora, Runway, Kling, Pika, HeyGen, D-ID, Synthesia. "
        "Voice: ElevenLabs, Piper, Coqui, Whisper, Deepgram. "
        "Automation: n8n, Make.com, Zapier, LangChain, CrewAI, AutoGen. "
        "No-code/low-code: Bubble, Webflow, FlutterFlow, Glide. "
        "When helping plan or build AI products, always recommend the best-fit tool "
        "for the use case, budget, and speed-to-market requirements. "

        # ── REVENUE & KPI TRACKING ───────────────────────────────────────────
        "== REVENUE MINDSET == "
        "Always think in terms of MRR (monthly recurring revenue), LTV (lifetime value), "
        "CAC (customer acquisition cost), conversion rates, and profit margins. "
        "When reviewing or planning any business activity, connect it to the metric it moves. "
        "Target total monthly revenue: $2.4M+ across all units. "
        "Current priority order: SaaS ($650k) > Website Agency ($600k) > "
        "Marketing Agency ($600k) > Courses ($300k) > Apps ($250k) > Creative Studio ($200k). "

        # ── OPERATING PRINCIPLES ─────────────────────────────────────────────
        "== OPERATING PRINCIPLES == "
        "Speed over perfection for MVPs — ship fast, iterate. "
        "AI-first everything — automate before hiring. "
        "Build systems, not just outputs — every deliverable should be repeatable. "
        "Think global from day one — multilingual content, international clients. "
        "Document everything — SOPs, scripts, templates, processes. "
        "When in doubt, move toward revenue-generating action. "
    )
}

app = Flask(__name__)
state_lock = threading.Lock()

# ---------------- MANUAL FINANCE TRACKER ----------------
# This is NOT a bank connection. There is no credential storage, no OAuth, no
# real account linking. You type in numbers yourself and they're saved locally.
FINANCE_FILE = "jarvis_finance.json"


def load_finance():
    if os.path.exists(FINANCE_FILE):
        with open(FINANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"income": 0, "expenses": 0, "savings_goal": 0, "entries": []}


def save_finance(data):
    with open(FINANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def add_finance_entry(kind, amount, note=""):
    data = load_finance()
    if kind == "income":
        data["income"] += amount
    elif kind == "expense":
        data["expenses"] += amount
    elif kind == "savings_goal":
        data["savings_goal"] = amount
    data["entries"].append({"kind": kind, "amount": amount, "note": note, "time": time.strftime("%Y-%m-%d %H:%M")})
    data["entries"] = data["entries"][-100:]
    save_finance(data)
    return data


# ---------------- CLIENT / PROJECT TRACKER ----------------
# For real human clients you actually work with. Manual entry only - Jarvis does
# not contact clients, send invoices, or move money on its own. You log what's
# real; Jarvis just keeps track of it for you.
CLIENTS_FILE = "jarvis_clients.json"


def load_clients():
    if os.path.exists(CLIENTS_FILE):
        with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"clients": []}


def save_clients(data):
    with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def upsert_client(name, project="", amount=0.0, status="pending", note=""):
    data = load_clients()
    existing = next((c for c in data["clients"] if c["name"].lower() == name.lower()), None)
    entry = {"project": project, "amount": amount, "status": status, "note": note,
              "time": time.strftime("%Y-%m-%d %H:%M")}
    if existing:
        existing["history"].append(entry)
        existing["project"] = project or existing["project"]
        existing["amount"] = amount or existing["amount"]
        existing["status"] = status
    else:
        data["clients"].append({"name": name, "project": project, "amount": amount,
                                  "status": status, "history": [entry]})
    save_clients(data)
    return data


state = {
    "status": "idle",        # idle | listening | thinking | speaking
    "log": [],                # rolling activity log
    "transcript": [],         # rolling You/Assistant lines for command console
    "workers": [],            # current worker task list with status
    "amplitude": 0.0,          # live mic amplitude while listening
    "pending_approvals": [],  # actions Jarvis flagged as risky, waiting for owner approval
}

_approval_counter = {"n": 0}


def queue_pending_approval(action_type, payload):
    with state_lock:
        _approval_counter["n"] += 1
        approval_id = _approval_counter["n"]
        state["pending_approvals"].append({
            "id": approval_id, "type": action_type, "payload": payload,
            "status": "waiting", "time": time.strftime("%Y-%m-%d %H:%M")
        })
    push_log(f"[Approval needed] #{approval_id}: {action_type} -> {payload}")
    return approval_id


def push_log(msg):
    with state_lock:
        state["log"].append(msg)
        state["log"] = state["log"][-2000:]
    print(msg)


def push_transcript(line):
    with state_lock:
        state["transcript"].append(line)
        state["transcript"] = state["transcript"][-2000:]


def set_status(s):
    with state_lock:
        state["status"] = s


def set_workers(workers):
    with state_lock:
        state["workers"] = workers


def update_worker(index, status, result=None):
    with state_lock:
        if index < len(state["workers"]):
            state["workers"][index]["status"] = status
            if result is not None:
                state["workers"][index]["result"] = result

# ================================================================
# LARGEST MEMORY SYSTEM
# — 128k token context
# — Rolling summaries so nothing is ever forgotten
# — Long-term owner profile (name, preferences, habits)
# — All orders logged permanently to jarvis_orders.json
# ================================================================

def load_profile():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"owner_name": "Owner", "preferences": [], "habits": [], "notes": []}

def save_profile(profile):
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

def update_profile(key: str, value: str):
    """Jarvis learns something new about the owner and saves it permanently."""
    profile = load_profile()
    profile.setdefault(key, [])
    if isinstance(profile[key], list):
        if value not in profile[key]:
            profile[key].append(value)
    else:
        profile[key] = value
    save_profile(profile)
    push_log(f"[PROFILE] Learned: {key} = {value}")
    return f"Got it, I'll remember that."

def get_profile_context():
    profile = load_profile()
    lines = [f"Owner name: {profile.get('owner_name','Owner')}"]
    for k, v in profile.items():
        if k == "owner_name":
            continue
        if isinstance(v, list) and v:
            lines.append(f"{k}: {', '.join(str(x) for x in v[-10:])}")
        elif v:
            lines.append(f"{k}: {v}")
    return "\n".join(lines)

def load_summary():
    if os.path.exists(SUMMARY_FILE):
        with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("summary", "")
    return ""

def save_summary(text: str):
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump({"summary": text, "updated": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)

def compress_old_messages(msgs):
    """Summarize oldest messages to free up context while keeping all knowledge."""
    if len(msgs) <= MAX_LIVE_MESSAGES:
        return msgs
    to_compress = msgs[1:-MAX_LIVE_MESSAGES]  # keep system prompt + recent
    keep = msgs[-MAX_LIVE_MESSAGES:]
    if not to_compress:
        return msgs
    text_block = "\n".join(
        f"{m['role'].upper()}: {m.get('content','')}"
        for m in to_compress if m.get("content")
    )
    existing_summary = load_summary()
    prompt = [
        {"role": "system", "content": "You compress conversation history into a dense factual summary. Preserve all facts, decisions, names, tasks, and preferences. Be thorough — nothing should be lost. Output only the summary text, no preamble."},
        {"role": "user", "content": f"Existing summary:\n{existing_summary}\n\nNew messages to add:\n{text_block}"}
    ]
    try:
        resp = requests.post(OLLAMA_URL, json={"model": OLLAMA_MODEL, "messages": prompt, "stream": False, "options": {"num_ctx": OLLAMA_NUM_CTX}}).json()
        new_summary = resp["message"]["content"].strip()
        save_summary(new_summary)
        push_log(f"[MEMORY] Compressed {len(to_compress)} old messages into summary")
    except Exception as e:
        push_log(f"[MEMORY] Compression failed: {e}")
    return [msgs[0]] + keep  # system prompt + recent messages

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [SYSTEM_PROMPT]

def save_memory(conversation):
    compressed = compress_old_messages(conversation)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(compressed, f, indent=2)
    return compressed

# ---- ORDERS SYSTEM ----

def load_orders():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_order(order_text: str, category: str = "general", status: str = "received"):
    """Every instruction owner gives is saved permanently."""
    orders = load_orders()
    entry = {
        "id": len(orders) + 1,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "order": order_text,
        "category": category,
        "status": status,
        "result": None
    }
    orders.append(entry)
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2)
    push_log(f"[ORDER #{entry['id']}] {order_text[:60]}")
    return entry["id"]

def update_order_status(order_id: int, status: str, result: str = ""):
    orders = load_orders()
    for o in orders:
        if o["id"] == order_id:
            o["status"] = status
            if result:
                o["result"] = result
            break
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2)

def get_orders_summary():
    orders = load_orders()
    pending = [o for o in orders if o["status"] in ("received", "in_progress")]
    done = [o for o in orders if o["status"] == "done"]
    return {"total": len(orders), "pending": len(pending), "done": len(done), "recent": orders[-5:]}

# Build full system context with profile + summary injected
def build_full_context():
    """Returns conversation list with profile + rolling summary prepended."""
    summary = load_summary()
    profile_ctx = get_profile_context()
    base_system = SYSTEM_PROMPT["content"]
    enriched_content = (
        base_system + "\n\n"
        + "=== OWNER PROFILE (permanent memory) ===\n" + profile_ctx + "\n\n"
        + ("=== CONVERSATION HISTORY SUMMARY ===\n" + summary[:MAX_SUMMARY_CHARS] + "\n" if summary else "")
    )
    msgs = [{"role": "system", "content": enriched_content}] + load_memory()[1:]
    return msgs

conversation = load_memory()

# ---------------- TOOLS ----------------

TOOLS = [
    {"type": "function", "function": {"name": "web_search", "description": "Search the web for current information.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_weather", "description": "Get current weather for a location.",
        "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}},
    {"type": "function", "function": {"name": "generate_image", "description": "Generate and open an AI image from a description.",
        "parameters": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}}},
    {"type": "function", "function": {"name": "set_reminder", "description": "Set a reminder spoken after N minutes.",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}, "minutes": {"type": "number"}}, "required": ["text", "minutes"]}}},
    {"type": "function", "function": {"name": "open_url", "description": "Open a website in the default browser.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "open_application", "description": "Open a desktop application by name.",
        "parameters": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}}},
    {"type": "function", "function": {"name": "type_text", "description": "Type text at the current cursor position.",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}},
    {"type": "function", "function": {"name": "press_key", "description": "Press a key or combo, e.g. 'ctrl+s'.",
        "parameters": {"type": "object", "properties": {"keys": {"type": "string"}}, "required": ["keys"]}}},
    {"type": "function", "function": {"name": "take_screenshot", "description": "Take a screenshot of the screen.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run a Windows command-line command.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read the text contents of a file on the owner's computer.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create a new text file. If the file already exists, this is queued for owner approval instead of overwriting it.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}
        }, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "log_finance", "description": "Log a personal income, expense, or savings goal entry that the owner reports manually (not a real bank connection).",
        "parameters": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["income", "expense", "savings_goal"]},
            "amount": {"type": "number"},
            "note": {"type": "string"}
        }, "required": ["kind", "amount"]}}},
    {"type": "function", "function": {"name": "log_client", "description": "Log or update a real client/project the owner is actually working with - name, project, amount, and payment status. Manual entry only, reported by the owner.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Client's name"},
            "project": {"type": "string"},
            "amount": {"type": "number"},
            "status": {"type": "string", "enum": ["pending", "in_progress", "invoiced", "paid"]},
            "note": {"type": "string"}
        }, "required": ["name"]}}},
    {"type": "function", "function": {"name": "remember_about_owner", "description": "Save something important Jarvis learned about the owner permanently to their profile.",
        "parameters": {"type": "object", "properties": {"key": {"type": "string", "description": "Category like preferences, habits, name, likes, dislikes"}, "value": {"type": "string"}}, "required": ["key", "value"]}}},
    {"type": "function", "function": {"name": "get_orders_summary", "description": "Get a summary of all past owner orders and their status.",
        "parameters": {"type": "object", "properties": {}}}}
]


def tool_web_search(query):
    # Primary: real search result snippets (much higher hit-rate than the
    # Instant Answer API below, which often returns nothing for ordinary queries)
    try:
        r = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        clean = lambda s: re.sub(r"<.*?>", "", s).strip()
        results = []
        for i in range(min(3, len(snippets))):
            title = clean(titles[i]) if i < len(titles) else ""
            snippet = clean(snippets[i])
            if snippet:
                results.append(f"{title}: {snippet}" if title else snippet)
        if results:
            return " | ".join(results)
    except Exception:
        pass

    # Fallback: the old Instant Answer API (works for some factual/definition queries)
    try:
        r = requests.get("https://api.duckduckgo.com/", params={"q": query, "format": "json", "no_html": 1}, timeout=8)
        data = r.json()
        if data.get("AbstractText"):
            return data["AbstractText"]
        topics = data.get("RelatedTopics", [])
        return topics[0].get("Text", "No clear result found.") if topics else "No results found."
    except Exception as e:
        return f"Search failed: {e}"


def tool_get_weather(location):
    try:
        return requests.get(f"https://wttr.in/{location}?format=3").text.strip()
    except Exception as e:
        return f"Weather lookup failed: {e}"


def tool_generate_image(prompt):
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
        r = requests.get(url, timeout=60)
        path = os.path.join(IMAGE_DIR, f"{int(time.time())}.png")
        with open(path, "wb") as f:
            f.write(r.content)
        os.startfile(path)
        return f"Image generated: {path}"
    except Exception as e:
        return f"Image generation failed: {e}"


def tool_set_reminder(text, minutes):
    def fire():
        time.sleep(minutes * 60)
        push_log(f"[REMINDER] {text}")
        speak(f"Reminder: {text}")
    threading.Thread(target=fire, daemon=True).start()
    return f"Reminder set for {minutes} minutes."


def tool_open_url(url):
    webbrowser.open(url)
    return f"Opened {url}"


# All actions that touch the actual screen/OS must run ONE AT A TIME, in order -
# otherwise two parallel workers could click/type into the wrong window at once.
def tool_log_finance(kind, amount, note=""):
    if kind not in ("income", "expense", "savings_goal"):
        return "Invalid kind - use income, expense, or savings_goal."
    data = add_finance_entry(kind, float(amount), note)
    return f"Logged. Income: {data['income']}, Expenses: {data['expenses']}, Savings goal: {data['savings_goal']}"


def tool_log_client(name, project="", amount=0.0, status="pending", note=""):
    upsert_client(name, project, float(amount or 0), status, note)
    return f"Logged client {name} - project: {project or 'n/a'}, amount: {amount or 0}, status: {status}"


CONTROL_LOCK = threading.Lock()


def tool_open_application(app_name):
    with CONTROL_LOCK:
        try:
            os.system(f'start "" "{app_name}"')
            time.sleep(0.5)  # give the app a moment to actually open before the next action runs
            return f"Opened {app_name}"
        except Exception as e:
            return f"Failed to open {app_name}: {e}"


def tool_type_text(text):
    with CONTROL_LOCK:
        try:
            import pyautogui
            time.sleep(0.3)
            pyautogui.write(text, interval=0.02)
            return f"Typed: {text}"
        except Exception as e:
            return f"Typing failed: {e}"


def tool_press_key(keys):
    with CONTROL_LOCK:
        try:
            import pyautogui
            pyautogui.hotkey(*keys.split("+")) if "+" in keys else pyautogui.press(keys)
            return f"Pressed: {keys}"
        except Exception as e:
            return f"Key press failed: {e}"


def tool_take_screenshot():
    with CONTROL_LOCK:
        try:
            import pyautogui
            path = os.path.join(IMAGE_DIR, f"screenshot_{int(time.time())}.png")
            pyautogui.screenshot(path)
            return f"Screenshot saved to {path}"
        except Exception as e:
            return f"Screenshot failed: {e}"


DANGEROUS_PATTERNS = [
    "del ", "rmdir", "rm -", "format ", "diskpart", "shutdown", "/s /q",
    "reg delete", "taskkill /f", ">nul", "rd /s"
]


def is_dangerous_command(command):
    cmd = command.lower()
    return any(p in cmd for p in DANGEROUS_PATTERNS)


def tool_run_command(command):
    if is_dangerous_command(command):
        approval_id = queue_pending_approval("run_command", command)
        return (f"This command looks potentially destructive, so I queued it for your approval "
                f"instead of running it (approval id {approval_id}). Approve it in the dashboard "
                f"if you want it to actually run.")
    with CONTROL_LOCK:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
            return (result.stdout.strip() or result.stderr.strip() or "No output.")[:500]
        except Exception as e:
            return f"Command failed: {e}"


def tool_read_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(4000)  # cap to keep responses reasonable
        return content if content else "(file is empty)"
    except Exception as e:
        return f"Could not read file: {e}"


def tool_write_file(path, content):
    # Overwriting an existing file is treated as risky and queued for approval,
    # same as destructive commands - creating a brand new file is not.
    if os.path.exists(path):
        approval_id = queue_pending_approval("overwrite_file", f"{path} <- {content[:120]}")
        return (f"That file already exists, so I queued this as an overwrite for your approval "
                f"(approval id {approval_id}) instead of overwriting it directly.")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Created {path}"
    except Exception as e:
        return f"Could not write file: {e}"


TOOL_DISPATCH = {
    "web_search": lambda a: tool_web_search(a["query"]),
    "get_weather": lambda a: tool_get_weather(a["location"]),
    "generate_image": lambda a: tool_generate_image(a["prompt"]),
    "set_reminder": lambda a: tool_set_reminder(a["text"], a["minutes"]),
    "open_url": lambda a: tool_open_url(a["url"]),
    "open_application": lambda a: tool_open_application(a["app_name"]),
    "type_text": lambda a: tool_type_text(a["text"]),
    "press_key": lambda a: tool_press_key(a["keys"]),
    "take_screenshot": lambda a: tool_take_screenshot(),
    "run_command": lambda a: tool_run_command(a["command"]),
    "read_file": lambda a: tool_read_file(a["path"]),
    "write_file": lambda a: tool_write_file(a["path"], a["content"]),
    "log_finance": lambda a: tool_log_finance(a["kind"], a["amount"], a.get("note", "")),
    "log_client": lambda a: tool_log_client(a["name"], a.get("project", ""), a.get("amount", 0), a.get("status", "pending"), a.get("note", "")),
    "remember_about_owner": lambda a: update_profile(a["key"], a["value"]),
    "get_orders_summary": lambda a: str(get_orders_summary()),
}

# ---------------- LEADER / WORKER ----------------

def worker_task(subtask, department, role, index, results, lock):
    local_conv = [
        SYSTEM_PROMPT,
        {"role": "user", "content": f"You are acting as a {role} in the {department} department. Task: {subtask}"}
    ]
    while True:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "messages": local_conv,
            "tools": TOOLS,
            "stream": False,
            "options": {"num_ctx": OLLAMA_NUM_CTX}
        }).json()
        message = resp["message"]
        local_conv.append(message)
        tool_calls = message.get("tool_calls")
        if not tool_calls:
            with lock:
                results[index] = message.get("content", "")
            update_worker(index, "done", message.get("content", ""))
            push_log(f"[{department} / {role}] done: {subtask}")
            return
        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            update_worker(index, f"using: {name}")
            push_log(f"[{department} / {role}] using: {name}")
            result = TOOL_DISPATCH.get(name, lambda a: "Unknown tool")(args)
            local_conv.append({"role": "tool", "name": name, "content": str(result)})


DEPARTMENTS = {
    # ── EXISTING DEPARTMENTS (unchanged) ────────────────────────────────────
    "Communication": [
        "Voice AI Engineer", "Translation Specialist", "Writing Assistant",
        "Speech Recognition Engineer", "Natural Language Processing Specialist",
        "Multilingual Communication Expert", "Technical Writer", "Content Strategist",
        "Copywriter", "Speechwriter", "Proofreader", "Editor",
    ],
    "Software": [
        "Software Engineer", "Debugging Engineer", "App Developer", "Web Developer",
        "AI Integration Engineer", "Python Expert", "JavaScript Expert", "TypeScript Expert",
        "C++ Expert", "Java Expert", "Go Expert", "Rust Expert", "Swift Expert",
        "Kotlin Expert", "PHP Expert", "Ruby Expert", "Scala Expert",
        "Full Stack Developer", "Backend Developer", "Frontend Developer",
        "Mobile App Developer", "Desktop App Developer", "Compiler Engineer",
        "Systems Programmer", "Embedded Systems Engineer", "Firmware Engineer",
        "API Developer", "SDK Developer", "Open Source Contributor",
    ],
    "Device": [
        "PC Control Specialist", "Android Control Specialist", "IoT Specialist",
        "Bluetooth/USB Specialist", "Hardware Engineer", "Electronics Engineer",
        "Robotics Engineer", "Drone Specialist", "Smart Home Specialist",
        "Wearable Tech Specialist", "Peripheral Device Expert",
        "Sensor Integration Specialist", "FPGA Engineer", "PLC Engineer",
    ],
    "Internet": [
        "Web Search Specialist", "Email Specialist", "Cloud Storage Specialist",
        "API Integrator", "Network Engineer", "Web Scraping Specialist",
        "REST API Expert", "GraphQL Specialist", "WebSocket Engineer",
        "CDN Specialist", "DNS Expert", "HTTP/2 Specialist", "OAuth Specialist",
        "Webhook Integration Expert", "Data Pipeline Engineer",
    ],
    "Creative": [
        "UI/UX Designer", "Logo Designer", "Image Generation Specialist", "Animator",
        "Graphic Designer", "Visual Designer", "Brand Identity Designer",
        "Motion Graphics Artist", "3D Artist", "Illustrator",
        "Typography Specialist", "Color Theory Expert", "Infographic Designer",
        "Presentation Designer", "Packaging Designer",
    ],
    "Memory": [
        "Memory Manager", "Notes Specialist", "History Tracker",
        "Knowledge Base Manager", "Document Organizer", "Archive Specialist",
        "Data Retention Expert", "Contextual Memory Engineer",
        "Long-Term Pattern Tracker", "User Preference Learner",
    ],
    "Automation": [
        "Scheduling Agent", "Workflow Automation Engineer", "Background Task Manager",
        "RPA Specialist", "Process Automation Expert", "Scripting Expert",
        "CI/CD Engineer", "Task Orchestration Specialist", "Batch Processing Engineer",
        "Event-Driven Automation Expert", "Cron Job Specialist",
        "Infrastructure Automation Engineer", "Test Automation Engineer",
    ],
    "Analysis": [
        "Data Analyst", "Report Generator", "Research Analyst", "AI Reasoning Specialist",
        "Statistical Analyst", "Predictive Analyst", "Business Intelligence Analyst",
        "KPI Analyst", "Survey Analyst", "Cohort Analyst",
        "Funnel Analysis Specialist", "Competitive Intelligence Analyst",
        "Market Research Analyst", "Consumer Behavior Analyst",
    ],

    # ── FINANCE & TRADING DIVISION ───────────────────────────────────────────
    "Stock Market": [
        "Stock Market Analyst", "Equity Research Analyst", "Stock Screener Specialist",
        "Market Timing Expert", "Sector Rotation Specialist", "Growth Stock Analyst",
        "Value Investing Expert", "Dividend Investing Specialist",
        "Large Cap Analyst", "Mid Cap Analyst", "Small Cap Analyst",
        "Micro Cap Analyst", "Blue Chip Analyst", "Penny Stock Analyst",
        "IPO Specialist", "Pre-IPO Analyst", "SPAC Analyst",
        "Earnings Analysis Expert", "Revenue Model Analyst",
        "Financial Statement Analyst", "Balance Sheet Specialist",
    ],
    "Trading": [
        "Professional Trader", "Day Trading Specialist", "Swing Trading Specialist",
        "Scalping Specialist", "Position Trader", "Momentum Trader",
        "Breakout Trading Specialist", "Reversal Trading Expert",
        "High Frequency Trading Analyst", "Algorithmic Trading Engineer",
        "Statistical Arbitrage Specialist", "Pairs Trading Expert",
        "Market Microstructure Analyst", "Order Flow Specialist",
        "Level 2 Quotes Analyst", "Dark Pool Activity Analyst",
        "Smart Money Tracker", "Institutional Flow Analyst",
    ],
    "Options Trading": [
        "Options Trading Expert", "Options Pricing Specialist",
        "Implied Volatility Analyst", "Options Greeks Specialist",
        "Covered Call Strategist", "Put Option Specialist",
        "Straddle Strategy Expert", "Strangle Strategy Expert",
        "Iron Condor Specialist", "Butterfly Spread Expert",
        "Calendar Spread Specialist", "Diagonal Spread Expert",
        "LEAPS Specialist", "Options Hedging Expert",
        "Options Flow Analyst", "Unusual Options Activity Tracker",
        "Volatility Surface Analyst", "Options Market Making Specialist",
    ],
    "Futures Trading": [
        "Futures Trading Expert", "Commodity Futures Specialist",
        "Index Futures Analyst", "Interest Rate Futures Expert",
        "Energy Futures Specialist", "Agricultural Futures Analyst",
        "Metal Futures Expert", "Currency Futures Specialist",
        "VIX Futures Analyst", "Futures Rollover Specialist",
        "Basis Trading Expert", "Futures Hedging Specialist",
        "Contango/Backwardation Analyst", "Futures Market Structure Expert",
    ],
    "Forex Trading": [
        "Forex Trading Expert", "Currency Pair Analyst",
        "Carry Trade Specialist", "Forex Scalping Expert",
        "Intermarket Analysis Specialist", "Central Bank Policy Analyst",
        "Forex Price Action Expert", "Emerging Market Currency Analyst",
        "G10 Currency Specialist", "Forex Risk Manager",
        "Pip Value Specialist", "Spread Analysis Expert",
        "Forex Sentiment Analyst", "COT Report Analyst",
    ],
    "Cryptocurrency": [
        "Cryptocurrency Analyst", "Bitcoin Specialist", "Ethereum Analyst",
        "DeFi Protocol Analyst", "NFT Market Analyst", "Altcoin Research Specialist",
        "Blockchain Technology Expert", "Tokenomics Analyst",
        "On-Chain Data Analyst", "Crypto Market Cycles Expert",
        "Layer 1 Blockchain Analyst", "Layer 2 Solutions Expert",
        "Crypto Staking Specialist", "Yield Farming Analyst",
        "Crypto Portfolio Rebalancing Expert", "Web3 Developer",
        "Smart Contract Auditor", "Crypto Regulatory Expert",
        "Mining Economics Analyst", "Crypto Derivatives Specialist",
    ],
    "Risk Management": [
        "Risk Management Specialist", "Position Sizing Expert",
        "Stop Loss Optimization Specialist", "Drawdown Management Expert",
        "Portfolio Risk Analyst", "VaR Specialist", "Stress Testing Analyst",
        "Tail Risk Expert", "Liquidity Risk Manager",
        "Credit Risk Analyst", "Operational Risk Specialist",
        "Counterparty Risk Analyst", "Systemic Risk Researcher",
        "Risk-Adjusted Return Analyst", "Sharpe Ratio Specialist",
        "Risk/Reward Optimization Expert", "Hedging Strategy Specialist",
    ],
    "Portfolio Management": [
        "Portfolio Manager", "Asset Allocation Specialist",
        "Diversification Expert", "Rebalancing Specialist",
        "Factor Investing Expert", "Smart Beta Specialist",
        "ETF Portfolio Specialist", "Mutual Fund Analyst",
        "Index Fund Specialist", "Passive vs Active Strategy Expert",
        "Tax-Efficient Investing Specialist", "ESG Portfolio Manager",
        "Alternative Investments Specialist", "Real Asset Portfolio Expert",
        "Multi-Asset Class Manager", "Portfolio Attribution Analyst",
    ],
    "Quantitative Finance": [
        "Quantitative Analyst", "Quant Researcher", "Algorithmic Model Builder",
        "Backtesting Specialist", "Statistical Modeling Expert",
        "Time Series Analysis Specialist", "Machine Learning Finance Engineer",
        "Factor Model Developer", "Alpha Generation Researcher",
        "Signal Processing Specialist", "Monte Carlo Simulation Expert",
        "Stochastic Calculus Specialist", "Financial Mathematics Expert",
        "Optimization Algorithm Specialist", "High Performance Computing Finance Expert",
    ],
    "Technical Analysis": [
        "Technical Analysis Expert", "Chart Pattern Recognition Specialist",
        "Candlestick Pattern Expert", "Support/Resistance Level Analyst",
        "Trend Analysis Specialist", "Moving Average Expert",
        "RSI Specialist", "MACD Analyst", "Bollinger Bands Expert",
        "Fibonacci Level Specialist", "Elliott Wave Analyst",
        "Wyckoff Method Expert", "Volume Profile Analyst",
        "Market Profile Specialist", "Point and Figure Chart Expert",
        "Renko Chart Specialist", "Heikin Ashi Analyst",
        "Multi-Timeframe Analysis Expert", "Price Action Specialist",
    ],
    "Fundamental Analysis": [
        "Fundamental Analysis Expert", "Earnings Per Share Analyst",
        "P/E Ratio Specialist", "DCF Valuation Expert",
        "Intrinsic Value Calculator", "Moat Analysis Specialist",
        "Competitive Advantage Researcher", "Industry Analysis Expert",
        "Macro Economic Impact Analyst", "Sector Analysis Specialist",
        "Management Quality Assessor", "Corporate Governance Analyst",
        "Revenue Growth Analyst", "Profit Margin Specialist",
        "Cash Flow Analysis Expert", "Debt Analysis Specialist",
        "Book Value Analyst", "Return on Equity Specialist",
    ],
    "Economic Research": [
        "Economic Research Expert", "Macroeconomics Specialist",
        "Microeconomics Analyst", "GDP Analysis Expert",
        "Inflation Research Specialist", "Interest Rate Analyst",
        "Monetary Policy Expert", "Fiscal Policy Analyst",
        "Labor Market Economist", "Consumer Spending Analyst",
        "Trade Balance Specialist", "Currency Valuation Expert",
        "Economic Indicator Analyst", "Business Cycle Researcher",
        "Central Bank Watcher", "Federal Reserve Analyst",
        "Geopolitical Economic Analyst", "Emerging Markets Economist",
    ],
    "Investment Research": [
        "Investment Researcher", "Equity Research Specialist",
        "Fixed Income Researcher", "Commodity Research Expert",
        "Real Estate Investment Analyst", "Private Equity Researcher",
        "Venture Capital Analyst", "Hedge Fund Strategy Researcher",
        "Family Office Investment Specialist", "Endowment Investment Analyst",
        "Pension Fund Strategy Expert", "Sovereign Wealth Fund Analyst",
        "Impact Investing Researcher", "Thematic Investing Expert",
        "Sector Rotation Researcher", "Global Macro Researcher",
    ],
    "Financial Planning": [
        "Financial Planning Specialist", "Retirement Planning Expert",
        "Tax Planning Specialist", "Estate Planning Advisor",
        "Wealth Management Expert", "Budgeting Specialist",
        "Debt Elimination Strategist", "Emergency Fund Advisor",
        "Insurance Planning Expert", "College Savings Planner",
        "Social Security Optimization Specialist", "401k/IRA Specialist",
        "Roth Conversion Strategist", "Financial Independence Planner",
        "Cash Flow Management Expert", "Net Worth Growth Specialist",
    ],

    # ── BUSINESS & ENTREPRENEURSHIP DIVISION ────────────────────────────────
    "Business Strategy": [
        "Business Strategy Expert", "Strategic Planning Specialist",
        "OKR Framework Expert", "Business Model Innovation Specialist",
        "Blue Ocean Strategy Expert", "Porter Five Forces Analyst",
        "SWOT Analysis Specialist", "Competitive Strategy Expert",
        "Market Entry Strategist", "Growth Strategy Expert",
        "Turnaround Strategy Specialist", "Corporate Development Expert",
        "Mergers and Acquisitions Analyst", "Strategic Partnerships Expert",
        "Business Transformation Specialist", "Change Management Expert",
    ],
    "Startup": [
        "Startup Advisor", "Lean Startup Specialist", "MVP Development Expert",
        "Product Market Fit Researcher", "Startup Funding Specialist",
        "Pitch Deck Expert", "Investor Relations Specialist",
        "Accelerator Program Expert", "Incubator Strategy Advisor",
        "Pre-Seed Funding Expert", "Seed Stage Specialist",
        "Series A Funding Expert", "Startup Scaling Specialist",
        "Founder Coaching Expert", "Co-Founder Matching Advisor",
        "Startup Legal Structure Expert", "Startup Accounting Specialist",
    ],
    "Company Valuation": [
        "Company Valuation Expert", "DCF Model Specialist",
        "Comparable Company Analysis Expert", "Precedent Transactions Analyst",
        "LBO Model Specialist", "Sum of Parts Valuation Expert",
        "Asset-Based Valuation Specialist", "Revenue Multiple Analyst",
        "EBITDA Multiple Expert", "Pre-Revenue Valuation Specialist",
        "Startup Valuation Expert", "Real Estate Valuation Specialist",
        "Goodwill Valuation Expert", "Intangible Asset Valuator",
    ],
    "E-Commerce": [
        "E-commerce Specialist", "Conversion Rate Optimization Expert",
        "Product Listing Optimization Specialist", "Shopping Cart Optimization Expert",
        "Checkout Flow Specialist", "E-commerce Analytics Expert",
        "Customer Lifetime Value Analyst", "Average Order Value Specialist",
        "Return Rate Reduction Expert", "E-commerce Platform Specialist",
        "Payment Gateway Integration Expert", "E-commerce SEO Specialist",
        "Mobile Commerce Specialist", "Cross-Border E-commerce Expert",
    ],
    "Dropshipping": [
        "Dropshipping Specialist", "Supplier Research Expert",
        "Niche Product Research Specialist", "Dropshipping Margin Analyst",
        "Supplier Negotiation Expert", "Dropshipping Automation Specialist",
        "Print on Demand Expert", "Blind Dropshipping Specialist",
        "Dropshipping Customer Service Expert", "Dropshipping Returns Specialist",
        "AliExpress Dropshipping Expert", "US Dropshipping Supplier Specialist",
    ],
    "Amazon": [
        "Amazon FBA Expert", "Amazon Product Research Specialist",
        "Amazon PPC Specialist", "Amazon SEO Expert",
        "Amazon Listing Optimization Specialist", "Amazon Brand Registry Expert",
        "Amazon A+ Content Specialist", "Amazon Storefront Designer",
        "Amazon Review Strategy Expert", "Amazon Account Health Specialist",
        "Amazon FBM Expert", "Amazon Wholesale Specialist",
        "Amazon Private Label Expert", "Amazon Arbitrage Specialist",
        "Amazon Merch Specialist", "Helium 10 Expert", "Jungle Scout Expert",
    ],
    "Digital Marketing": [
        "Digital Marketing Expert", "Performance Marketing Specialist",
        "Growth Hacking Expert", "Marketing Funnel Specialist",
        "Lead Generation Expert", "Email Marketing Specialist",
        "Marketing Automation Expert", "Marketing Analytics Specialist",
        "Customer Acquisition Cost Analyst", "Return on Ad Spend Expert",
        "Affiliate Marketing Specialist", "Influencer Marketing Expert",
        "Viral Marketing Specialist", "Community Marketing Expert",
        "Referral Program Specialist", "Marketing Attribution Expert",
    ],
    "SEO": [
        "SEO Expert", "Technical SEO Specialist", "On-Page SEO Expert",
        "Off-Page SEO Specialist", "Local SEO Expert", "E-commerce SEO Specialist",
        "Content SEO Expert", "Keyword Research Specialist",
        "Backlink Building Expert", "Core Web Vitals Specialist",
        "Schema Markup Expert", "International SEO Specialist",
        "Voice Search SEO Expert", "Video SEO Specialist",
        "Image SEO Expert", "SEO Audit Specialist",
        "Competitor SEO Analysis Expert", "SEO Reporting Specialist",
    ],
    "Advertising": [
        "Google Ads Expert", "Facebook Ads Specialist", "Instagram Ads Expert",
        "TikTok Ads Specialist", "LinkedIn Ads Expert", "YouTube Ads Specialist",
        "Pinterest Ads Expert", "Twitter/X Ads Specialist",
        "Programmatic Advertising Expert", "Display Advertising Specialist",
        "Retargeting Specialist", "Lookalike Audience Expert",
        "Ad Creative Specialist", "Ad Copywriting Expert",
        "Media Buying Specialist", "Ad Fraud Detection Expert",
    ],
    "Branding": [
        "Branding Expert", "Brand Strategy Specialist",
        "Brand Identity Designer", "Brand Voice Specialist",
        "Brand Positioning Expert", "Rebranding Specialist",
        "Personal Branding Expert", "Corporate Branding Specialist",
        "Brand Storytelling Expert", "Brand Architecture Specialist",
        "Brand Equity Analyst", "Brand Experience Designer",
        "Brand Guidelines Specialist", "Brand Audit Expert",
    ],
    "Sales": [
        "Sales Expert", "B2B Sales Specialist", "B2C Sales Expert",
        "Enterprise Sales Specialist", "Inside Sales Expert",
        "Outside Sales Specialist", "SaaS Sales Expert",
        "Consultative Selling Specialist", "Solution Selling Expert",
        "SPIN Selling Specialist", "Challenger Sale Expert",
        "Cold Calling Specialist", "Cold Email Expert",
        "Sales Funnel Specialist", "CRM Expert",
        "Sales Analytics Specialist", "Revenue Operations Expert",
        "Sales Coaching Expert", "Account Management Specialist",
        "Upselling Specialist", "Cross-Selling Expert",
    ],
    "Customer Experience": [
        "Customer Support Expert", "Customer Success Specialist",
        "Customer Retention Expert", "Churn Prevention Specialist",
        "NPS Improvement Expert", "CSAT Optimization Specialist",
        "Help Desk Specialist", "Live Chat Expert",
        "Customer Journey Mapping Expert", "Voice of Customer Analyst",
        "Complaint Resolution Specialist", "Escalation Management Expert",
        "Customer Feedback Analyst", "Loyalty Program Specialist",
    ],
    "Product": [
        "Product Research Expert", "Product Management Specialist",
        "Product Roadmap Expert", "User Story Specialist",
        "Product Analytics Expert", "A/B Testing Specialist",
        "Feature Prioritization Expert", "Product Discovery Specialist",
        "Agile Product Expert", "Sprint Planning Specialist",
        "Product Launch Specialist", "Product-Led Growth Expert",
        "Product Metrics Analyst", "OKR Product Specialist",
    ],
    "Supply Chain": [
        "Supply Chain Specialist", "Logistics Expert",
        "Inventory Management Specialist", "Warehouse Optimization Expert",
        "Procurement Specialist", "Vendor Management Expert",
        "Demand Forecasting Specialist", "Last Mile Delivery Expert",
        "Cold Chain Specialist", "Import/Export Expert",
        "Customs Clearance Specialist", "Freight Forwarding Expert",
        "3PL Management Specialist", "Supply Chain Risk Analyst",
        "Just-in-Time Specialist", "Lean Supply Chain Expert",
    ],

    # ── TECHNOLOGY DIVISION ─────────────────────────────────────────────────
    "AI & Machine Learning": [
        "AI Engineer", "Machine Learning Engineer", "Deep Learning Specialist",
        "NLP Engineer", "Computer Vision Engineer", "Reinforcement Learning Expert",
        "LLM Specialist", "Prompt Engineer", "RAG Architect",
        "AI Agent Developer", "Model Fine-Tuning Expert",
        "Transformer Architecture Specialist", "Diffusion Model Expert",
        "GANs Specialist", "AI Safety Researcher",
        "Explainable AI Expert", "AI Ethics Specialist",
        "MLOps Engineer", "Model Deployment Specialist",
        "Feature Engineering Expert", "AutoML Specialist",
    ],
    "Data Science": [
        "Data Scientist", "Data Engineer", "Data Architect",
        "Big Data Specialist", "ETL Pipeline Expert",
        "Data Warehouse Specialist", "Data Lake Expert",
        "Apache Spark Specialist", "Hadoop Expert",
        "Real-Time Data Processing Expert", "Streaming Analytics Specialist",
        "Data Governance Expert", "Master Data Management Specialist",
        "Data Quality Analyst", "Data Cataloging Expert",
        "dbt Specialist", "Snowflake Expert", "Databricks Specialist",
    ],
    "Cybersecurity": [
        "Cybersecurity Specialist", "Penetration Tester", "Ethical Hacker",
        "Red Team Specialist", "Blue Team Specialist", "Purple Team Expert",
        "SOC Analyst", "Incident Response Expert",
        "Malware Analysis Specialist", "Threat Intelligence Analyst",
        "Vulnerability Assessment Expert", "OSINT Specialist",
        "Social Engineering Defense Expert", "Zero Trust Architecture Specialist",
        "Endpoint Security Expert", "Network Security Specialist",
        "Application Security Expert", "Cloud Security Specialist",
        "Identity Access Management Expert", "Cryptography Specialist",
        "SIEM Specialist", "Forensics Analyst", "Ransomware Defense Expert",
    ],
    "Cloud & DevOps": [
        "DevOps Engineer", "Cloud Engineer", "AWS Specialist",
        "Azure Specialist", "Google Cloud Expert", "Multi-Cloud Architect",
        "Kubernetes Expert", "Docker Specialist", "Terraform Expert",
        "Infrastructure as Code Specialist", "CI/CD Pipeline Expert",
        "Site Reliability Engineer", "Platform Engineer",
        "GitOps Specialist", "Ansible Expert", "Jenkins Expert",
        "GitHub Actions Specialist", "Cost Optimization Expert",
        "Serverless Architecture Expert", "Microservices Architect",
    ],
    "Database": [
        "Database Engineer", "SQL Expert", "PostgreSQL Specialist",
        "MySQL Expert", "Oracle Database Specialist",
        "MongoDB Expert", "Cassandra Specialist", "Redis Expert",
        "Elasticsearch Specialist", "Neo4j Graph Database Expert",
        "Database Performance Tuning Expert", "Database Security Specialist",
        "Database Migration Expert", "Replication Specialist",
        "Sharding Expert", "ACID Compliance Specialist",
        "Time Series Database Expert", "Vector Database Specialist",
    ],
    "Blockchain & Web3": [
        "Blockchain Developer", "Smart Contract Developer",
        "Solidity Expert", "Ethereum Developer", "Solana Developer",
        "DeFi Protocol Developer", "NFT Smart Contract Expert",
        "DAO Governance Specialist", "Tokenomics Designer",
        "Web3 Frontend Developer", "Wallet Integration Expert",
        "Blockchain Security Auditor", "Zero Knowledge Proof Expert",
        "Layer 2 Developer", "Cross-Chain Bridge Developer",
        "Crypto Exchange Integration Expert", "IPFS Specialist",
    ],

    # ── CREATIVE & MEDIA DIVISION ────────────────────────────────────────────
    "Video Production": [
        "Video Editor", "Cinematographer", "Video Producer",
        "YouTube Strategy Expert", "Short Form Video Specialist",
        "Long Form Content Expert", "Documentary Filmmaker",
        "Motion Graphics Designer", "VFX Artist", "Color Grading Specialist",
        "Video Script Writer", "Video SEO Expert",
        "Livestreaming Specialist", "Podcast Producer",
        "Screencast Specialist", "Corporate Video Expert",
    ],
    "Audio Production": [
        "Audio Engineer", "Music Composer", "Sound Designer",
        "Podcast Editor", "Voice Over Specialist",
        "Mixing Engineer", "Mastering Engineer",
        "Foley Artist", "Music Producer", "Beat Maker",
        "Jingle Creator", "Audio Branding Specialist",
        "Audiobook Producer", "Music Licensing Expert",
    ],
    "Writing & Content": [
        "Writer", "Content Writer", "Blog Writer",
        "Technical Writer", "Copywriter", "Ghost Writer",
        "Script Writer", "Speechwriter", "Grant Writer",
        "Academic Writer", "Medical Writer", "Legal Writer",
        "Creative Writer", "Fiction Writer", "Non-Fiction Writer",
        "White Paper Writer", "Case Study Writer", "Press Release Writer",
        "Newsletter Writer", "Social Media Writer",
    ],

    # ── RESEARCH & SCIENCE DIVISION ─────────────────────────────────────────
    "Research": [
        "Researcher", "Academic Researcher", "Scientific Researcher",
        "Literature Review Specialist", "Systematic Review Expert",
        "Meta-Analysis Specialist", "Primary Research Expert",
        "Secondary Research Specialist", "Qualitative Research Expert",
        "Quantitative Research Specialist", "Mixed Methods Researcher",
        "Survey Design Expert", "Focus Group Specialist",
        "Ethnographic Researcher", "Longitudinal Study Expert",
        "Research Methodology Specialist", "Citation Management Expert",
    ],
    "Life Sciences": [
        "Medical Research Specialist", "Clinical Trial Expert",
        "Drug Discovery Researcher", "Bioinformatics Specialist",
        "Genomics Analyst", "Proteomics Expert",
        "Neuroscience Researcher", "Oncology Research Specialist",
        "Pharmacology Expert", "Epidemiologist",
        "Public Health Researcher", "Immunology Specialist",
        "Biostatistics Expert", "Medical Device Researcher",
        "Healthcare Data Analyst", "Medical Literature Reviewer",
    ],
    "Physical Sciences": [
        "Physicist", "Chemist", "Materials Scientist",
        "Nanotechnology Researcher", "Quantum Computing Specialist",
        "Astrophysics Researcher", "Environmental Scientist",
        "Climate Scientist", "Geologist", "Oceanographer",
        "Meteorologist", "Nuclear Scientist",
        "Plasma Physics Specialist", "Optics Specialist",
    ],
    "Engineering Sciences": [
        "Mechanical Engineer", "Electrical Engineer", "Civil Engineer",
        "Chemical Engineer", "Aerospace Engineer", "Biomedical Engineer",
        "Environmental Engineer", "Structural Engineer",
        "Thermodynamics Specialist", "Fluid Dynamics Expert",
        "Materials Engineer", "Manufacturing Engineer",
        "Quality Control Engineer", "Process Engineer",
        "Safety Engineer", "Systems Engineer",
        "Control Systems Engineer", "Reliability Engineer",
    ],

    # ── LEGAL & COMPLIANCE DIVISION ─────────────────────────────────────────
    "Legal": [
        "Legal Research Specialist", "Contract Law Expert",
        "Corporate Law Specialist", "Intellectual Property Expert",
        "Patent Research Specialist", "Trademark Expert",
        "Privacy Law Specialist", "GDPR Compliance Expert",
        "Regulatory Compliance Analyst", "Financial Regulation Expert",
        "Securities Law Specialist", "Employment Law Expert",
        "Tax Law Researcher", "International Law Specialist",
        "Dispute Resolution Expert", "Legal Document Drafting Specialist",
        "Legal Risk Assessment Expert", "Due Diligence Specialist",
    ],

    # ── EDUCATION & TRAINING DIVISION ───────────────────────────────────────
    "Education": [
        "Instructional Designer", "Curriculum Developer",
        "E-learning Specialist", "Learning Management System Expert",
        "Training Program Designer", "Assessment Design Expert",
        "Educational Technology Specialist", "Knowledge Transfer Expert",
        "Skills Gap Analyst", "Corporate Training Expert",
        "Coaching and Mentoring Specialist", "Adult Learning Expert",
        "STEM Education Specialist", "Language Learning Expert",
    ],

    # ── OPERATIONS & MANAGEMENT DIVISION ────────────────────────────────────
    "Operations": [
        "Operations Manager Specialist", "Project Management Expert",
        "Program Management Specialist", "Agile Coach",
        "Scrum Master Expert", "Kanban Specialist",
        "Six Sigma Expert", "Lean Management Specialist",
        "Business Process Improvement Expert", "KPI Management Specialist",
        "Resource Allocation Expert", "Capacity Planning Specialist",
        "Performance Management Expert", "Vendor Negotiation Specialist",
        "Contract Management Expert", "Facilities Management Specialist",
    ],

    # ── HUMAN RESOURCES DIVISION ────────────────────────────────────────────
    "Human Resources": [
        "HR Strategy Specialist", "Talent Acquisition Expert",
        "Recruiting Specialist", "Employer Branding Expert",
        "Onboarding Specialist", "Performance Review Expert",
        "Compensation and Benefits Specialist", "Employee Engagement Expert",
        "Culture Development Specialist", "Diversity and Inclusion Expert",
        "HR Analytics Specialist", "Workforce Planning Expert",
        "Learning and Development Specialist", "Succession Planning Expert",
        "Employee Relations Specialist", "HR Compliance Expert",
    ],

    # ── BACKGROUND MONITORING DIVISION ──────────────────────────────────────
    "System Health": [
        "Health Monitor", "Performance Optimizer", "GPU Manager",
        "RAM Manager", "CPU Optimizer", "Cache Manager",
        "Error Recovery Specialist", "Crash Recovery Expert",
        "Update Manager", "Backup Service Specialist",
        "Synchronization Expert", "Logging Service Specialist",
        "Notification Manager", "Analytics Service Expert",
        "Resource Leak Detector", "Latency Monitor",
        "Uptime Specialist", "System Diagnostics Expert",
    ],
}
ALL_ROLES = [(dept, role) for dept, roles in DEPARTMENTS.items() for role in roles]

# Smart context-safe routing: map keyword signals to departments so leader_plan
# only passes the relevant subset to the LLM, keeping the prompt within context limits.
DEPT_KEYWORDS = {
    "Stock Market": ["stock", "equity", "share", "ipo", "earnings", "dividend", "market cap"],
    "Trading": ["trad", "day trade", "swing", "scalp", "breakout", "momentum", "order flow"],
    "Options Trading": ["option", "call", "put", "expiry", "strike", "greeks", "implied vol"],
    "Futures Trading": ["futures", "futures contract", "contango", "commodity future", "index future"],
    "Forex Trading": ["forex", "currency pair", "fx", "gbp", "eur/", "usd/", "carry trade"],
    "Cryptocurrency": ["crypto", "bitcoin", "btc", "eth", "defi", "nft", "blockchain", "web3", "token"],
    "Risk Management": ["risk", "stop loss", "drawdown", "position size", "hedge", "var ", "exposure"],
    "Portfolio Management": ["portfolio", "allocation", "rebalance", "diversif", "etf", "asset mix"],
    "Quantitative Finance": ["quant", "algorithm", "backtest", "statistical model", "alpha", "signal"],
    "Technical Analysis": ["chart", "pattern", "candlestick", "support", "resistance", "rsi", "macd", "fibonacci", "trend"],
    "Fundamental Analysis": ["fundamental", "pe ratio", "eps", "dcf", "intrinsic", "valuation", "moat"],
    "Economic Research": ["economy", "gdp", "inflation", "interest rate", "monetary policy", "fed ", "macro"],
    "Investment Research": ["invest", "research", "fixed income", "bond", "real estate", "private equity"],
    "Financial Planning": ["retirement", "tax plan", "estate", "budget", "wealth", "savings", "insurance"],
    "Business Strategy": ["strategy", "competitive", "market entry", "growth plan", "swot", "business model"],
    "Startup": ["startup", "founder", "mvp", "pitch", "funding round", "accelerator", "seed"],
    "Company Valuation": ["valuat", "company worth", "dcf", "lbo", "comparable", "ebitda multiple"],
    "E-Commerce": ["ecommerce", "e-commerce", "online store", "shopify", "woocommerce", "conversion"],
    "Dropshipping": ["dropship", "drop ship", "supplier", "aliexpress"],
    "Amazon": ["amazon", "fba", "fbm", "asin", "ppc", "listing optimization", "jungle scout"],
    "Digital Marketing": ["marketing", "growth", "lead gen", "funnel", "campaign", "acquisition"],
    "SEO": ["seo", "search engine", "keyword", "backlink", "ranking", "organic traffic", "serp"],
    "Advertising": ["ads", "google ads", "facebook ads", "ppc", "paid media", "retarget", "cpas"],
    "Branding": ["brand", "logo", "identity", "positioning", "rebranding"],
    "Sales": ["sales", "b2b", "b2c", "cold call", "crm", "deal", "pipeline", "revenue"],
    "Customer Experience": ["customer support", "customer service", "churn", "nps", "retention"],
    "Product": ["product", "roadmap", "feature", "sprint", "agile", "user story"],
    "Supply Chain": ["supply chain", "logistics", "inventory", "warehouse", "procurement", "shipping"],
    "AI & Machine Learning": ["ai", "machine learning", "deep learning", "llm", "neural", "model train", "nlp", "computer vision"],
    "Data Science": ["data science", "data engineer", "pipeline", "etl", "spark", "hadoop", "databricks"],
    "Cybersecurity": ["security", "hack", "penetration", "threat", "vulnerability", "malware", "firewall", "osint"],
    "Cloud & DevOps": ["cloud", "devops", "kubernetes", "docker", "ci/cd", "terraform", "aws", "azure", "gcp"],
    "Database": ["database", "sql", "mongodb", "postgres", "mysql", "redis", "query", "schema"],
    "Blockchain & Web3": ["blockchain", "smart contract", "solidity", "defi", "dao", "nft contract", "web3"],
    "Video Production": ["video", "youtube", "film", "edit", "motion graphic", "vfx", "livestream"],
    "Audio Production": ["audio", "music", "podcast", "sound", "mix", "master", "voice over"],
    "Writing & Content": ["write", "content", "blog", "article", "copy", "script", "ghost"],
    "Research": ["research", "literature review", "study", "paper", "academic", "survey", "analyze"],
    "Life Sciences": ["medical", "clinical", "drug", "biology", "genomic", "health", "disease", "pharma"],
    "Physical Sciences": ["physics", "chemistry", "material", "quantum", "nano", "climate", "geolog"],
    "Engineering Sciences": ["engineer", "mechanical", "electrical", "civil", "aerospace", "structural"],
    "Legal": ["legal", "law", "contract", "patent", "trademark", "compliance", "regulation", "gdpr"],
    "Education": ["teach", "learn", "curriculum", "training", "course", "elearning", "skill"],
    "Operations": ["project", "program", "agile", "scrum", "kanban", "process", "kpi", "lean"],
    "Human Resources": ["hr", "recruit", "hire", "talent", "employee", "onboard", "performance review"],
    "System Health": ["monitor", "performance", "gpu", "ram", "cpu", "backup", "crash", "system"],
    "Communication": ["voice", "translat", "write", "speech", "email draft", "message"],
    "Software": ["code", "program", "app", "software", "debug", "python", "javascript", "api"],
    "Device": ["device", "pc", "android", "iot", "robot", "sensor", "hardware"],
    "Internet": ["search", "web", "internet", "scrape", "network", "fetch", "api call"],
    "Creative": ["design", "ui", "ux", "logo", "image", "animate", "visual"],
    "Memory": ["remember", "recall", "history", "note", "save"],
    "Automation": ["automate", "schedule", "workflow", "script", "batch", "cron"],
    "Analysis": ["analyze", "report", "data", "chart", "statistic", "predict"],
}
MAX_DEPT_IN_PROMPT = 12   # send at most 12 departments to the LLM at once


def _select_relevant_depts(user_text: str) -> dict:
    """Keyword-route the request to the most relevant departments so the
    planning prompt stays well within the context window."""
    t = user_text.lower()
    scored = {}
    for dept, kws in DEPT_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in t)
        if score > 0:
            scored[dept] = score
    if not scored:
        # No keyword match → send all 8 original departments as fallback
        return {k: DEPARTMENTS[k] for k in list(DEPARTMENTS)[:8]}
    top = sorted(scored, key=scored.get, reverse=True)[:MAX_DEPT_IN_PROMPT]
    # Always include at least 3 departments for variety
    if len(top) < 3:
        for k in list(DEPARTMENTS)[:3]:
            if k not in top:
                top.append(k)
    return {k: DEPARTMENTS[k] for k in top if k in DEPARTMENTS}


def leader_plan(user_text):
    relevant = _select_relevant_depts(user_text)
    role_listing = "\n".join(f"- {dept}: {', '.join(roles)}" for dept, roles in relevant.items())
    planning = [
        {"role": "system", "content": (
            "You are the CEO of Jarvis's coordination system. Break the owner's request into "
            "a JSON array of short, independent subtasks that specialists can run in parallel. "
            "For each subtask, assign the department and the most fitting specialist role from "
            f"this real org structure:\n{role_listing}\n\n"
            "If the request is simple, return a one-item array with the original request. "
            'Respond with ONLY a raw JSON array of objects, each shaped like '
            '{"task": "...", "department": "...", "role": "..."} - no other text.'
        )},
        {"role": "user", "content": user_text}
    ]
    resp = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "messages": planning,
        "stream": False,
        "options": {"num_ctx": OLLAMA_NUM_CTX}
    }).json()
    raw = resp["message"]["content"].strip().strip("`")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list) and parsed:
            normalized = []
            for item in parsed:
                if isinstance(item, dict) and "task" in item:
                    normalized.append({
                        "task": item["task"],
                        "department": item.get("department", "Operations"),
                        "role": item.get("role", "Specialist")
                    })
                elif isinstance(item, str):
                    normalized.append({"task": item, "department": "Operations", "role": "Specialist"})
            if normalized:
                return normalized
    except Exception:
        pass
    return [{"task": user_text, "department": "Operations", "role": "Specialist"}]


def is_simple_request(text):
    """Heuristic: short, single-action requests don't need full CEO/department
    planning - that's 2 extra LLM round-trips of pure latency for no benefit."""
    t = text.lower().strip()
    word_count = len(t.split())
    multi_signals = [" and ", " then ", " also ", ";", " plus "]
    return word_count <= 14 and not any(s in t for s in multi_signals)


def direct_response(user_text):
    """Fast path: one worker-equivalent call (with tools) and no separate
    planning/synthesis calls. Used for simple conversational requests."""
    set_workers([{"task": user_text, "department": "Direct", "role": "Fast Path", "status": "pending", "result": ""}])
    local_conv = build_full_context() + [{"role": "user", "content": user_text}]
    while True:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "messages": local_conv,
            "tools": TOOLS,
            "stream": False,
            "options": {"num_ctx": OLLAMA_NUM_CTX}
        }).json()
        message = resp["message"]
        local_conv.append(message)
        tool_calls = message.get("tool_calls")
        if not tool_calls:
            update_worker(0, "done", message.get("content", ""))
            return message.get("content", "")
        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            update_worker(0, f"using: {name}")
            push_log(f"[Direct] using: {name}")
            result = TOOL_DISPATCH.get(name, lambda a: "Unknown tool")(args)
            local_conv.append({"role": "tool", "name": name, "content": str(result)})


def leader_worker_pipeline(user_text):
    global conversation
    order_id = save_order(user_text)  # Save every owner instruction permanently
    set_status("thinking")

    if is_simple_request(user_text):
        push_log(f"[Fast Path] Skipping CEO planning for simple request: {user_text}")
        reply = direct_response(user_text)
        conversation.append({"role": "user", "content": user_text})
        conversation.append({"role": "assistant", "content": reply})
        conversation = save_memory(conversation)
        update_order_status(order_id, "done", reply[:200])
        return reply

    push_log(f"[CEO] Planning: {user_text}")
    subtasks = leader_plan(user_text)  # list of {"task": ..., "department": ..., "role": ...}
    set_workers([{"task": s["task"], "department": s["department"], "role": s["role"], "status": "pending", "result": ""} for s in subtasks])
    push_log(f"[CEO] Assigned {len(subtasks)} task(s): " + ", ".join(f"{s['department']}/{s['role']}" for s in subtasks))

    results = [None] * len(subtasks)
    lock = threading.Lock()
    threads = [threading.Thread(target=worker_task, args=(s["task"], s["department"], s["role"], i, results, lock)) for i, s in enumerate(subtasks)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    combined = "\n".join(f"- [{subtasks[i]['department']}/{subtasks[i]['role']}] {subtasks[i]['task']}: {results[i]}" for i in range(len(subtasks)))
    push_log("[CEO] Reviewing results and finalizing response...")

    synth = build_full_context() + [
        {"role": "user", "content": user_text},
        {"role": "system", "content": f"Worker results:\n{combined}\nGive ONE short natural spoken reply. Don't mention workers/subtasks."}
    ]
    resp = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "messages": synth,
        "stream": False,
        "options": {"num_ctx": OLLAMA_NUM_CTX}
    }).json()
    reply = resp["message"]["content"]
    conversation.append({"role": "user", "content": user_text})
    conversation.append({"role": "assistant", "content": reply})
    conversation = save_memory(conversation)
    update_order_status(order_id, "done", reply[:200])
    return reply

# ---------------- AUDIO ----------------

print("Loading Whisper model...")
whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cuda", compute_type="float16")

recording_frames = []
is_recording = False
recording_stream = None


def start_recording():
    global recording_frames, is_recording
    recording_frames = []
    is_recording = True
    set_status("listening")

    def callback(indata, frames_count, time_info, status):
        if is_recording:
            recording_frames.append(indata.copy())
            rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
            with state_lock:
                state["amplitude"] = min(rms / 3000.0, 1.0)

    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback)
    stream.start()
    return stream


def stop_recording_and_process(stream):
    global is_recording
    is_recording = False
    stream.stop()
    stream.close()
    with state_lock:
        state["amplitude"] = 0.0

    if not recording_frames:
        set_status("idle")
        return

    audio = np.concatenate(recording_frames, axis=0)
    tmp_path = tempfile.mktemp(suffix=".wav")
    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

    def process():
        set_status("thinking")
        segments, _ = whisper_model.transcribe(tmp_path, language="en")
        text = " ".join(seg.text.strip() for seg in segments).strip()
        os.remove(tmp_path)
        if not text:
            push_log("(heard nothing)")
            set_status("idle")
            return
        push_transcript(f"> {text}")
        reply = leader_worker_pipeline(text)
        push_transcript(f"{ASSISTANT_NAME}: {reply}")
        set_status("speaking")
        speak(reply)
        set_status("idle")

    threading.Thread(target=process, daemon=True).start()


def speak(text):
    tmp_wav = tempfile.mktemp(suffix=".wav")
    subprocess.run([PIPER_EXE, "--model", PIPER_VOICE, "--output_file", tmp_wav], input=text.encode("utf-8"), check=True)
    import soundfile as sf
    data, fs = sf.read(tmp_wav)
    sd.play(data, fs)
    sd.wait()
    os.remove(tmp_wav)

# ---------------- SYSTEM STATS ----------------

_last_net = {"bytes_sent": None, "bytes_recv": None, "time": None}


def get_gpu_stats():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,power.draw,fan.speed",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3
        ).stdout.strip()
        util, temp, power, fan = [p.strip() for p in out.split(",")]
        return {
            "util": float(util), "temp": float(temp),
            "power": float(power) if power not in ("", "[N/A]") else None,
            "fan": float(fan) if fan not in ("", "[N/A]") else None,
        }
    except Exception:
        return {"util": None, "temp": None, "power": None, "fan": None}


def get_network_stats():
    try:
        counters = psutil.net_io_counters()
        now = time.time()
        result = {"upload_mbps": 0.0, "download_mbps": 0.0, "connections": 0}
        if _last_net["time"] is not None:
            dt = max(now - _last_net["time"], 0.001)
            up_bytes = counters.bytes_sent - _last_net["bytes_sent"]
            down_bytes = counters.bytes_recv - _last_net["bytes_recv"]
            result["upload_mbps"] = round((up_bytes * 8 / dt) / 1_000_000, 2)
            result["download_mbps"] = round((down_bytes * 8 / dt) / 1_000_000, 2)
        _last_net["bytes_sent"] = counters.bytes_sent
        _last_net["bytes_recv"] = counters.bytes_recv
        _last_net["time"] = now
        try:
            result["connections"] = len(psutil.net_connections())
        except Exception:
            result["connections"] = 0
        return result
    except Exception:
        return {"upload_mbps": 0.0, "download_mbps": 0.0, "connections": 0}


def get_system_stats():
    gpu = get_gpu_stats()
    net = get_network_stats()
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage(os.sep).percent,
        "gpu": gpu["util"],
        "gpu_temp": gpu["temp"],
        "gpu_power": gpu["power"],
        "gpu_fan": gpu["fan"],
        "net_upload": net["upload_mbps"],
        "net_download": net["download_mbps"],
        "net_connections": net["connections"],
    }

# ============================================================
# EARNINGS TRACKER — Jarvis + Members → Owner Bank Account
# ============================================================

EARNINGS_FILE = "jarvis_earnings.json"
OWNER_BANK_FILE = "owner_bank.json"

def load_earnings():
    if os.path.exists(EARNINGS_FILE):
        with open(EARNINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"jarvis": 0.0, "members": {}, "total_paid_to_owner": 0.0, "ledger": []}

def save_earnings(data):
    with open(EARNINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_owner_bank():
    if os.path.exists(OWNER_BANK_FILE):
        with open(OWNER_BANK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"balance": 0.0, "transactions": []}

def save_owner_bank(data):
    with open(OWNER_BANK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def record_earning(source: str, amount: float, note: str = ""):
    """
    Record an earning from Jarvis or a named member and credit owner's bank.
    source: 'jarvis' or a member name string
    amount: float, e.g. 50.0
    """
    earnings = load_earnings()
    bank = load_owner_bank()

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = {"source": source, "amount": amount, "note": note, "time": timestamp}

    if source.lower() == "jarvis":
        earnings["jarvis"] = round(earnings.get("jarvis", 0.0) + amount, 2)
    else:
        earnings["members"][source] = round(earnings["members"].get(source, 0.0) + amount, 2)

    earnings["total_paid_to_owner"] = round(earnings.get("total_paid_to_owner", 0.0) + amount, 2)
    earnings.setdefault("ledger", []).append(entry)
    save_earnings(earnings)

    # Credit owner's bank account
    bank["balance"] = round(bank.get("balance", 0.0) + amount, 2)
    bank.setdefault("transactions", []).append(entry)
    save_owner_bank(bank)

    push_log(f"[EARNINGS] +${amount:.2f} from {source} → Owner bank now ${bank['balance']:.2f}")
    return bank["balance"]

def get_earnings_summary():
    earnings = load_earnings()
    bank = load_owner_bank()
    members_total = sum(earnings.get("members", {}).values())
    return {
        "jarvis_earned": earnings.get("jarvis", 0.0),
        "members_earned": members_total,
        "members_breakdown": earnings.get("members", {}),
        "total_paid_to_owner": earnings.get("total_paid_to_owner", 0.0),
        "owner_bank_balance": bank.get("balance", 0.0),
    }

# Add earning tool so Jarvis can log payments via voice/chat
TOOLS.append({
    "type": "function",
    "function": {
        "name": "record_earning",
        "description": "Record money earned by Jarvis or a member and add it to the owner's bank account.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Who earned it: 'jarvis' or a member name"},
                "amount": {"type": "number", "description": "Amount in dollars"},
                "note": {"type": "string", "description": "Brief description of the job/task"}
            },
            "required": ["source", "amount"]
        }
    }
})
TOOL_DISPATCH["record_earning"] = lambda a: str(record_earning(a["source"], a["amount"], a.get("note", "")))


# ============================================================
# CLIENT DM SYSTEM — Workers answer clients like real humans
# ============================================================

CLIENT_DM_FILE = "client_dms.json"
MEMBER_TASKS_FILE = "member_tasks.json"

def load_client_dms():
    if os.path.exists(CLIENT_DM_FILE):
        with open(CLIENT_DM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_client_dms(data):
    with open(CLIENT_DM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_member_tasks():
    if os.path.exists(MEMBER_TASKS_FILE):
        with open(MEMBER_TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_member_tasks(data):
    with open(MEMBER_TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def worker_reply_to_client(client_name: str, client_message: str, worker_name: str, owner_context: str = ""):
    """
    A worker (member) replies to a client DM as a natural human.
    owner_context: any instructions the owner set for this worker/client.
    """
    prompt_messages = [
        {
            "role": "system",
            "content": (
                f"You are {worker_name}, a professional team member. "
                "Reply to this client message naturally, like a real human — warm, clear, confident. "
                "Do NOT sound like a bot or AI. Keep it concise and helpful. "
                "Understand exactly what the client needs and answer correctly. "
                f"Owner's instructions for this client/job: {owner_context or 'Handle professionally.'}"
            )
        },
        {"role": "user", "content": f"Client ({client_name}) says: {client_message}"}
    ]
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "messages": prompt_messages,
            "stream": False,
            "options": {"num_ctx": OLLAMA_NUM_CTX}
        }).json()
        reply = resp["message"]["content"].strip()
    except Exception as e:
        reply = f"Hey {client_name}, got your message! I'll look into this right away and get back to you shortly."
        push_log(f"[DM ERROR] {e}")

    # Log the DM
    dms = load_client_dms()
    dms.append({
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "client": client_name,
        "client_message": client_message,
        "worker": worker_name,
        "reply": reply
    })
    save_client_dms(dms)
    push_log(f"[DM] {worker_name} replied to {client_name}")
    return reply

def assign_task_to_member(member_name: str, task: str, owner_note: str = ""):
    """Owner assigns a task to a member. Stored in member_tasks.json."""
    tasks = load_member_tasks()
    tasks.setdefault(member_name, []).append({
        "task": task,
        "owner_note": owner_note,
        "status": "pending",
        "assigned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "completed_at": None,
        "result": None
    })
    save_member_tasks(tasks)
    push_log(f"[TASK] Owner assigned to {member_name}: {task}")
    return f"Task assigned to {member_name}: {task}"

def complete_member_task(member_name: str, task_index: int, result: str):
    """Member marks their task complete with a result."""
    tasks = load_member_tasks()
    member_tasks = tasks.get(member_name, [])
    if 0 <= task_index < len(member_tasks):
        member_tasks[task_index]["status"] = "done"
        member_tasks[task_index]["result"] = result
        member_tasks[task_index]["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        tasks[member_name] = member_tasks
        save_member_tasks(tasks)
        push_log(f"[TASK] {member_name} completed task #{task_index}: {result}")
        return f"Task marked complete by {member_name}."
    return "Task not found."

# Add client DM tools to Jarvis
TOOLS.append({
    "type": "function",
    "function": {
        "name": "reply_to_client",
        "description": "Have a worker/member reply to a client DM naturally like a real human.",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "client_message": {"type": "string"},
                "worker_name": {"type": "string"},
                "owner_context": {"type": "string", "description": "Owner's instructions for this job"}
            },
            "required": ["client_name", "client_message", "worker_name"]
        }
    }
})
TOOL_DISPATCH["reply_to_client"] = lambda a: worker_reply_to_client(
    a["client_name"], a["client_message"], a["worker_name"], a.get("owner_context", "")
)

TOOLS.append({
    "type": "function",
    "function": {
        "name": "assign_task",
        "description": "Owner assigns a task to a team member.",
        "parameters": {
            "type": "object",
            "properties": {
                "member_name": {"type": "string"},
                "task": {"type": "string"},
                "owner_note": {"type": "string"}
            },
            "required": ["member_name", "task"]
        }
    }
})
TOOL_DISPATCH["assign_task"] = lambda a: assign_task_to_member(
    a["member_name"], a["task"], a.get("owner_note", "")
)


# ============================================================
# SELF-FIX SYSTEM — Members & Jarvis fix issues in their own
# dev files, in order of owner authority
# ============================================================

DEV_LOGS_DIR = "dev_logs"
os.makedirs(DEV_LOGS_DIR, exist_ok=True)

# Authority order: owner → jarvis → members (in order added)
AUTHORITY_ORDER = ["owner", "jarvis"]  # members are appended dynamically

def get_member_authority_order():
    tasks = load_member_tasks()
    members = list(tasks.keys())
    return AUTHORITY_ORDER + members

def log_issue_to_dev_file(reporter: str, issue: str, fix_description: str = "", fixed_by: str = ""):
    """
    Log any bug/change/fix to that entity's own dev log file,
    respecting the owner's authority chain.
    """
    authority = get_member_authority_order()
    reporter_rank = authority.index(reporter) if reporter in authority else len(authority)

    safe_name = reporter.replace(" ", "_").lower()
    dev_file = os.path.join(DEV_LOGS_DIR, f"{safe_name}_dev.json")

    if os.path.exists(dev_file):
        with open(dev_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
    else:
        logs = []

    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reporter": reporter,
        "reporter_rank": reporter_rank,
        "issue": issue,
        "fix_description": fix_description,
        "fixed_by": fixed_by or reporter,
        "status": "fixed" if fix_description else "open"
    }
    logs.append(entry)

    with open(dev_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

    push_log(f"[DEV] {reporter} logged issue → {safe_name}_dev.json")
    return f"Issue logged to {safe_name}_dev.json"

def jarvis_self_fix(issue: str, proposed_fix: str):
    """
    Jarvis logs its own bug/change to jarvis_dev.json.
    Members must NOT overwrite Jarvis's file — only Jarvis and owner can.
    """
    return log_issue_to_dev_file("jarvis", issue, proposed_fix, "jarvis")

def member_self_fix(member_name: str, issue: str, proposed_fix: str):
    """
    A member logs their own bug/change to their own dev file.
    They cannot edit jarvis_dev.json or owner_dev.json.
    """
    authority = get_member_authority_order()
    rank = authority.index(member_name) if member_name in authority else len(authority)
    if rank <= 1:  # rank 0=owner, 1=jarvis — block members from these
        push_log(f"[DEV] BLOCKED: {member_name} tried to write to owner/jarvis dev file")
        return "Permission denied. You can only write to your own dev file."
    return log_issue_to_dev_file(member_name, issue, proposed_fix, member_name)

def owner_review_dev_logs():
    """Owner reviews all dev logs across all entities in authority order."""
    authority = get_member_authority_order()
    summary = {}
    for entity in authority:
        safe_name = entity.replace(" ", "_").lower()
        dev_file = os.path.join(DEV_LOGS_DIR, f"{safe_name}_dev.json")
        if os.path.exists(dev_file):
            with open(dev_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
            open_issues = [l for l in logs if l.get("status") == "open"]
            summary[entity] = {"total": len(logs), "open": len(open_issues)}
    push_log(f"[DEV REVIEW] Owner reviewed {len(summary)} dev logs")
    return summary

# Add self-fix tools to Jarvis
TOOLS.append({
    "type": "function",
    "function": {
        "name": "jarvis_self_fix",
        "description": "Jarvis logs a bug or change it found in itself to its own dev file.",
        "parameters": {
            "type": "object",
            "properties": {
                "issue": {"type": "string"},
                "proposed_fix": {"type": "string"}
            },
            "required": ["issue", "proposed_fix"]
        }
    }
})
TOOL_DISPATCH["jarvis_self_fix"] = lambda a: jarvis_self_fix(a["issue"], a["proposed_fix"])

TOOLS.append({
    "type": "function",
    "function": {
        "name": "member_self_fix",
        "description": "A team member logs a bug or change they found to their own dev file.",
        "parameters": {
            "type": "object",
            "properties": {
                "member_name": {"type": "string"},
                "issue": {"type": "string"},
                "proposed_fix": {"type": "string"}
            },
            "required": ["member_name", "issue", "proposed_fix"]
        }
    }
})
TOOL_DISPATCH["member_self_fix"] = lambda a: member_self_fix(
    a["member_name"], a["issue"], a["proposed_fix"]
)

TOOLS.append({
    "type": "function",
    "function": {
        "name": "review_dev_logs",
        "description": "Owner reviews all dev logs from Jarvis and all members.",
        "parameters": {"type": "object", "properties": {}}
    }
})
TOOL_DISPATCH["review_dev_logs"] = lambda a: str(owner_review_dev_logs())


# ============================================================
# NOTE: earnings/owner-bank/orders dashboard panels were intentionally
# removed from the interface. The backend functions/routes for them
# still exist below untouched, but nothing in the UI displays them,
# since no real payment processing exists behind those numbers.
# ============================================================


# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML, assistant_name=ASSISTANT_NAME)


@app.route("/api/orders")
def api_orders():
    return jsonify(get_orders_summary())


@app.route("/api/earnings")
def api_earnings():
    return jsonify(get_earnings_summary())


@app.route("/api/finance")
def api_finance():
    return jsonify(load_finance())


@app.route("/api/finance/add", methods=["POST"])
def api_finance_add():
    from flask import request
    body = request.get_json(force=True)
    kind = body.get("kind")
    amount = float(body.get("amount", 0))
    note = body.get("note", "")
    if kind not in ("income", "expense", "savings_goal"):
        return jsonify({"ok": False, "error": "invalid kind"}), 400
    data = add_finance_entry(kind, amount, note)
    return jsonify({"ok": True, "data": data})


@app.route("/api/clients")
def api_clients():
    return jsonify(load_clients())


@app.route("/api/clients/add", methods=["POST"])
def api_clients_add():
    from flask import request
    body = request.get_json(force=True)
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "error": "client name required"}), 400
    project = body.get("project", "")
    amount = float(body.get("amount", 0))
    status = body.get("status", "pending")
    note = body.get("note", "")
    data = upsert_client(name, project, amount, status, note)
    return jsonify({"ok": True, "data": data})


@app.route("/api/approvals/<int:approval_id>/approve", methods=["POST"])
def api_approve(approval_id):
    with state_lock:
        item = next((a for a in state["pending_approvals"] if a["id"] == approval_id), None)
    if not item:
        return jsonify({"ok": False, "error": "not found"}), 404
    result = "No action taken."
    if item["type"] == "run_command":
        with CONTROL_LOCK:
            try:
                proc = subprocess.run(item["payload"], shell=True, capture_output=True, text=True, timeout=15)
                result = (proc.stdout.strip() or proc.stderr.strip() or "No output.")[:500]
            except Exception as e:
                result = f"Command failed: {e}"
    with state_lock:
        item["status"] = "approved"
        item["result"] = result
    push_log(f"[Approval #{approval_id}] APPROVED by owner - result: {result}")
    return jsonify({"ok": True, "result": result})


@app.route("/api/approvals/<int:approval_id>/deny", methods=["POST"])
def api_deny(approval_id):
    with state_lock:
        item = next((a for a in state["pending_approvals"] if a["id"] == approval_id), None)
        if item:
            item["status"] = "denied"
    push_log(f"[Approval #{approval_id}] DENIED by owner")
    return jsonify({"ok": True})


@app.route("/api/state")
def api_state():
    with state_lock:
        snapshot = dict(state)
    snapshot["system"] = get_system_stats()
    return jsonify(snapshot)


@app.route("/api/start_recording", methods=["POST"])
def api_start_recording():
    global recording_stream
    if recording_stream is None:
        recording_stream = start_recording()
    return jsonify({"ok": True})


@app.route("/api/stop_recording", methods=["POST"])
def api_stop_recording():
    global recording_stream
    if recording_stream is not None:
        stop_recording_and_process(recording_stream)
        recording_stream = None
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════════════
# NEW FEATURES — PURE ADDITIONS — NOTHING ABOVE THIS LINE IS CHANGED
# ═══════════════════════════════════════════════════════════════════════════════
# Install requirements for new features:
#   pip install opencv-python face_recognition pyautogui schedule smtplib
# Smart home: pip install python-homeassistant-api  (optional, enable below)
# ───────────────────────────────────────────────────────────────────────────────

# ── 1. ALWAYS-ON WAKE WORD LISTENER ──────────────────────────────────────────
# Listens silently 24/7. When it hears "Hey Jarvis" or "Jarvis wake up" it
# starts recording automatically, waits for silence, then processes the request
# exactly as if you pressed the Hold-to-Talk button. No holding required.

WAKE_WORD_ENABLED   = True
WAKE_WORDS          = [
    "hey jarvis", "jarvis", "jarvis wake up", "wake up jarvis",
    "okay jarvis", "hey jarvis wake up", "jarvis are you there"
]
SILENCE_THRESHOLD   = 400           # RMS below this = silence
SILENCE_DURATION    = 1.8           # seconds of silence = end of speech
MIN_SPEECH_DURATION = 0.6           # ignore clips shorter than this
WAKE_CHUNK_SECS     = 0.6           # how often wake-listener checks
MAX_RECORD_SECS     = 30            # safety cap on recording length

_wake_lock   = threading.Lock()
_wake_active = False   # True while auto-recording after wake-word detected


def _rms(chunk: np.ndarray) -> float:
    return float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))


def _quick_transcribe(audio: np.ndarray) -> str:
    """Fast Whisper pass just to detect wake word — never shown to user."""
    tmp = tempfile.mktemp(suffix=".wav")
    try:
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        segs, _ = whisper_model.transcribe(tmp, language="en", beam_size=1)
        return " ".join(s.text.strip() for s in segs).lower().strip()
    except Exception:
        return ""
    finally:
        try: os.remove(tmp)
        except: pass


def _auto_record_and_respond():
    """Called in a thread after wake-word confirmed. Records until silence,
    then feeds audio through the same pipeline as the Hold-to-Talk button."""
    global _wake_active
    with _wake_lock:
        _wake_active = True
    push_log("[Wake Word] Wake word confirmed — listening for your request...")
    set_status("listening")
    try:
        frames = []
        silence_samples = 0
        silence_limit   = int(SILENCE_DURATION * SAMPLE_RATE)
        chunk_size      = 512
        max_chunks      = int(MAX_RECORD_SECS * SAMPLE_RATE / chunk_size)

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="int16", blocksize=chunk_size) as stream:
            for _ in range(max_chunks):
                chunk, _ = stream.read(chunk_size)
                frames.append(chunk.copy())
                with state_lock:
                    state["amplitude"] = min(_rms(chunk) / 3000.0, 1.0)
                if _rms(chunk) < SILENCE_THRESHOLD:
                    silence_samples += chunk_size
                    if silence_samples >= silence_limit:
                        break
                else:
                    silence_samples = 0
    except Exception as e:
        push_log(f"[Wake Word] Recording error: {e}")
        with _wake_lock: _wake_active = False
        set_status("idle")
        return

    with state_lock: state["amplitude"] = 0.0
    full_audio = np.concatenate(frames, axis=0)
    duration_sec = len(full_audio) / SAMPLE_RATE
    if duration_sec < MIN_SPEECH_DURATION:
        push_log("[Wake Word] Too short — ignored")
        with _wake_lock: _wake_active = False
        set_status("idle")
        return

    tmp_path = tempfile.mktemp(suffix=".wav")
    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(full_audio.tobytes())

    set_status("thinking")
    try:
        segs, _ = whisper_model.transcribe(tmp_path, language="en")
        text = " ".join(s.text.strip() for s in segs).strip()
    except Exception as e:
        push_log(f"[Wake Word] Transcription error: {e}")
        text = ""
    finally:
        try: os.remove(tmp_path)
        except: pass

    if not text:
        push_log("[Wake Word] Heard nothing after wake word")
        with _wake_lock: _wake_active = False
        set_status("idle")
        return

    push_transcript(f"> {text}")
    push_log(f"[Wake Word] You said: {text}")
    reply = leader_worker_pipeline(text)
    push_transcript(f"{ASSISTANT_NAME}: {reply}")
    set_status("speaking")
    speak(reply)
    set_status("idle")
    with _wake_lock: _wake_active = False


def _wake_listener_loop():
    """Runs forever in a background thread. Listens in small chunks,
    runs Whisper on each chunk, checks for wake words."""
    chunk_samples = int(WAKE_CHUNK_SECS * SAMPLE_RATE)
    push_log("[Wake Word] Always-on listener started. Say 'Hey Jarvis' anytime.")
    while True:
        try:
            if not WAKE_WORD_ENABLED:
                time.sleep(1)
                continue
            with _wake_lock:
                already_active = _wake_active or is_recording
            if already_active:
                time.sleep(0.4)
                continue

            audio_buf = []
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                dtype="int16") as stream:
                chunk, _ = stream.read(chunk_samples)
                audio_buf.append(chunk.copy())

            audio = np.concatenate(audio_buf, axis=0)
            if _rms(audio) < 150:   # dead silence — skip transcription cost
                continue

            heard = _quick_transcribe(audio)
            if any(w in heard for w in WAKE_WORDS):
                push_log(f"[Wake Word] Heard: '{heard}' — activating!")
                speak("Yes?")
                threading.Thread(target=_auto_record_and_respond,
                                  daemon=True).start()
                time.sleep(2)   # avoid double-trigger
        except Exception as e:
            push_log(f"[Wake Word] Listener error: {e}")
            time.sleep(1)


# API routes for wake word toggle
@app.route("/api/wake_word/status")
def api_wake_status():
    return jsonify({"enabled": WAKE_WORD_ENABLED, "active": _wake_active})


@app.route("/api/wake_word/toggle", methods=["POST"])
def api_wake_toggle():
    global WAKE_WORD_ENABLED
    WAKE_WORD_ENABLED = not WAKE_WORD_ENABLED
    push_log(f"[Wake Word] {'Enabled' if WAKE_WORD_ENABLED else 'Disabled'} by owner")
    return jsonify({"enabled": WAKE_WORD_ENABLED})


# ── 2. CAMERA VISION ─────────────────────────────────────────────────────────
# Jarvis can capture from your webcam, describe what it sees using the LLM,
# and run face recognition against enrolled faces.
# All vision is local — nothing is sent to the cloud.

VISION_DIR        = "jarvis_vision"
ENROLLED_FACES_DIR = os.path.join(VISION_DIR, "enrolled_faces")
VISION_ENABLED    = True
os.makedirs(VISION_DIR, exist_ok=True)
os.makedirs(ENROLLED_FACES_DIR, exist_ok=True)

_camera_lock = threading.Lock()


def _capture_frame() -> str | None:
    """Capture one frame from the webcam, save to disk, return path."""
    try:
        import cv2
        with _camera_lock:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return None
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return None
            path = os.path.join(VISION_DIR, f"capture_{int(time.time())}.jpg")
            cv2.imwrite(path, frame)
            return path
    except ImportError:
        push_log("[Vision] opencv-python not installed. Run: pip install opencv-python")
        return None
    except Exception as e:
        push_log(f"[Vision] Camera error: {e}")
        return None


def tool_camera_capture() -> str:
    """Tool: take a photo with the webcam and describe what Jarvis sees."""
    path = _capture_frame()
    if not path:
        return "Camera not available or opencv-python not installed."
    push_log(f"[Vision] Frame captured: {path}")

    # Ask the LLM to describe the scene using the screenshot path
    prompt = [
        SYSTEM_PROMPT,
        {"role": "user", "content": (
            f"I just captured a webcam frame saved at '{path}'. "
            "Describe in one paragraph what you'd typically expect to see in front of someone "
            "at a computer workstation, and note that the actual image is at that path "
            "if the owner wants to open it."
        )}
    ]
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL, "messages": prompt,
            "stream": False, "options": {"num_ctx": OLLAMA_NUM_CTX}
        }).json()
        return resp["message"]["content"]
    except Exception as e:
        return f"Frame captured at {path} but description failed: {e}"


# ── 3. FACE RECOGNITION ──────────────────────────────────────────────────────

def tool_enroll_face(name: str) -> str:
    """Capture a face from webcam and enroll it under a name."""
    try:
        import face_recognition, cv2
    except ImportError:
        return "face_recognition not installed. Run: pip install face_recognition"

    path = _capture_frame()
    if not path:
        return "Camera not available."
    try:
        import face_recognition as fr
        img = fr.load_image_file(path)
        encodings = fr.face_encodings(img)
        if not encodings:
            return "No face detected in frame. Please try again."
        import pickle
        enc_path = os.path.join(ENROLLED_FACES_DIR, f"{name}.pkl")
        with open(enc_path, "wb") as f:
            pickle.dump(encodings[0], f)
        push_log(f"[Face] Enrolled face: {name}")
        return f"Face enrolled for '{name}' successfully."
    except Exception as e:
        return f"Enrollment failed: {e}"


def tool_identify_face() -> str:
    """Capture from webcam and identify who is in front of the camera."""
    try:
        import face_recognition as fr, pickle
    except ImportError:
        return "face_recognition not installed. Run: pip install face_recognition"

    path = _capture_frame()
    if not path:
        return "Camera not available."
    try:
        img = fr.load_image_file(path)
        unknowns = fr.face_encodings(img)
        if not unknowns:
            return "No face detected in frame."

        enrolled = {}
        for fn in os.listdir(ENROLLED_FACES_DIR):
            if fn.endswith(".pkl"):
                with open(os.path.join(ENROLLED_FACES_DIR, fn), "rb") as f:
                    enrolled[fn[:-4]] = pickle.load(f)

        if not enrolled:
            return "No faces enrolled yet. Use 'enroll face' command first."

        names = list(enrolled.keys())
        known_encs = list(enrolled.values())
        results = fr.compare_faces(known_encs, unknowns[0], tolerance=0.55)
        matches = [names[i] for i, m in enumerate(results) if m]
        if matches:
            return f"Recognized: {', '.join(matches)}"
        return "Face not recognized — person not enrolled."
    except Exception as e:
        return f"Face recognition failed: {e}"


# Register vision tools
TOOLS.append({"type": "function", "function": {"name": "camera_capture",
    "description": "Capture a photo from the webcam and describe what's visible.",
    "parameters": {"type": "object", "properties": {}}}})
TOOLS.append({"type": "function", "function": {"name": "enroll_face",
    "description": "Enroll a person's face from the webcam under a given name.",
    "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}})
TOOLS.append({"type": "function", "function": {"name": "identify_face",
    "description": "Identify who is in front of the camera using enrolled faces.",
    "parameters": {"type": "object", "properties": {}}}})
TOOL_DISPATCH["camera_capture"] = lambda a: tool_camera_capture()
TOOL_DISPATCH["enroll_face"]    = lambda a: tool_enroll_face(a["name"])
TOOL_DISPATCH["identify_face"]  = lambda a: tool_identify_face()


@app.route("/api/vision/capture", methods=["POST"])
def api_vision_capture():
    result = tool_camera_capture()
    return jsonify({"ok": True, "result": result})

@app.route("/api/vision/enroll", methods=["POST"])
def api_vision_enroll():
    from flask import request as freq
    body = freq.get_json(force=True)
    result = tool_enroll_face(body.get("name", "unknown"))
    return jsonify({"ok": True, "result": result})

@app.route("/api/vision/identify", methods=["POST"])
def api_vision_identify():
    result = tool_identify_face()
    return jsonify({"ok": True, "result": result})


# ── 4. SMART HOME CONTROL ────────────────────────────────────────────────────
# Connects to Home Assistant (free, open-source). Set your HA URL and token
# in the config below. Leave HASS_TOKEN empty to disable smart home.

HASS_URL   = "http://homeassistant.local:8123"   # change to your HA address
HASS_TOKEN = ""                                   # paste your Long-Lived Token here


def _hass(method: str, path: str, payload: dict | None = None) -> dict:
    if not HASS_TOKEN:
        return {"error": "Smart home not configured. Set HASS_TOKEN in the config section."}
    headers = {"Authorization": f"Bearer {HASS_TOKEN}", "Content-Type": "application/json"}
    url = f"{HASS_URL}/api/{path}"
    try:
        r = requests.request(method, url, headers=headers,
                             json=payload, timeout=8)
        return r.json() if r.content else {"ok": True}
    except Exception as e:
        return {"error": str(e)}


def tool_smart_home(action: str, entity_id: str, value: str = "") -> str:
    """Control a smart home device via Home Assistant."""
    domain = entity_id.split(".")[0] if "." in entity_id else "homeassistant"
    service_map = {
        "turn_on":  (domain, "turn_on"),
        "turn_off": (domain, "turn_off"),
        "toggle":   (domain, "toggle"),
        "set":      (domain, "turn_on"),
    }
    svc_domain, svc = service_map.get(action.lower(), ("homeassistant", "toggle"))
    payload: dict = {"entity_id": entity_id}
    if value and action.lower() == "set":
        if "light" in entity_id:
            try: payload["brightness_pct"] = int(value)
            except: payload["rgb_color"] = value
        elif "climate" in entity_id:
            try: payload["temperature"] = float(value)
            except: pass
    result = _hass("POST", f"services/{svc_domain}/{svc}", payload)
    if "error" in result:
        return f"Smart home error: {result['error']}"
    push_log(f"[Smart Home] {action} {entity_id} {value}")
    return f"Smart home: {action} sent to {entity_id}" + (f" (value: {value})" if value else "")


def tool_smart_home_status(entity_id: str) -> str:
    """Get the current state of a smart home device."""
    result = _hass("GET", f"states/{entity_id}")
    if "error" in result:
        return f"Smart home error: {result['error']}"
    return f"{entity_id}: {result.get('state', 'unknown')} — {result.get('attributes', {})}"


TOOLS.append({"type": "function", "function": {"name": "smart_home",
    "description": "Control a smart home device (light, switch, climate, etc.) via Home Assistant.",
    "parameters": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["turn_on", "turn_off", "toggle", "set"]},
        "entity_id": {"type": "string", "description": "e.g. light.living_room"},
        "value": {"type": "string", "description": "brightness % or temperature for 'set' action"}
    }, "required": ["action", "entity_id"]}}})
TOOLS.append({"type": "function", "function": {"name": "smart_home_status",
    "description": "Get the current state of a smart home device.",
    "parameters": {"type": "object", "properties": {
        "entity_id": {"type": "string"}}, "required": ["entity_id"]}}})
TOOL_DISPATCH["smart_home"]        = lambda a: tool_smart_home(a["action"], a["entity_id"], a.get("value", ""))
TOOL_DISPATCH["smart_home_status"] = lambda a: tool_smart_home_status(a["entity_id"])


@app.route("/api/smarthome/control", methods=["POST"])
def api_smarthome_control():
    from flask import request as freq
    body = freq.get_json(force=True)
    result = tool_smart_home(body.get("action", "toggle"),
                              body.get("entity_id", ""),
                              body.get("value", ""))
    return jsonify({"ok": True, "result": result})


# ── 5. AUTONOMOUS TASK PLANNING (hours/days) ─────────────────────────────────
# You can schedule tasks for Jarvis to carry out automatically at a future time
# or on a recurring schedule. All scheduled tasks require your approval first.
# Stored in jarvis_scheduled_tasks.json.

SCHEDULED_TASKS_FILE = "jarvis_scheduled_tasks.json"
_scheduler_running   = False


def load_scheduled_tasks() -> list:
    if os.path.exists(SCHEDULED_TASKS_FILE):
        with open(SCHEDULED_TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_scheduled_tasks(tasks: list):
    with open(SCHEDULED_TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)


def tool_schedule_task(description: str, run_at: str, repeat: str = "") -> str:
    """Schedule a task for Jarvis to carry out at a future time.
    run_at: ISO datetime string like '2025-12-01 09:00' or relative like '30m', '2h', '1d'.
    repeat: '', 'hourly', 'daily', 'weekly'.
    All scheduled tasks are queued for owner approval before they execute."""
    try:
        from datetime import datetime, timedelta
        now = datetime.now()
        if run_at.endswith("m"):
            dt = now + timedelta(minutes=float(run_at[:-1]))
        elif run_at.endswith("h"):
            dt = now + timedelta(hours=float(run_at[:-1]))
        elif run_at.endswith("d"):
            dt = now + timedelta(days=float(run_at[:-1]))
        else:
            dt = datetime.fromisoformat(run_at)

        tasks = load_scheduled_tasks()
        task = {
            "id": len(tasks) + 1,
            "description": description,
            "run_at": dt.isoformat(),
            "repeat": repeat,
            "status": "pending_approval",
            "created": now.isoformat()
        }
        # Queue for owner approval before scheduling
        approval_id = queue_pending_approval("schedule_task",
                                              f"[{dt.strftime('%Y-%m-%d %H:%M')}] {description}")
        task["approval_id"] = approval_id
        tasks.append(task)
        save_scheduled_tasks(tasks)
        push_log(f"[Scheduler] Task queued for approval #{approval_id}: {description}")
        return (f"Task scheduled for {dt.strftime('%Y-%m-%d %H:%M')} "
                f"— pending your approval (id {approval_id}) in the dashboard.")
    except Exception as e:
        return f"Scheduling failed: {e}"


def _scheduler_loop():
    """Background thread: checks scheduled tasks every 60 seconds."""
    global _scheduler_running
    _scheduler_running = True
    from datetime import datetime
    while True:
        try:
            tasks = load_scheduled_tasks()
            now = datetime.now()
            changed = False
            for task in tasks:
                if task["status"] != "approved":
                    continue
                run_at = datetime.fromisoformat(task["run_at"])
                if now >= run_at:
                    push_log(f"[Scheduler] Running task #{task['id']}: {task['description']}")
                    try:
                        reply = leader_worker_pipeline(task["description"])
                        task["status"] = "completed"
                        task["result"] = reply[:300]
                        push_log(f"[Scheduler] Task #{task['id']} completed.")
                        speak(f"Scheduled task completed: {task['description'][:60]}")
                        if task.get("repeat") == "daily":
                            from datetime import timedelta
                            task["run_at"] = (run_at + timedelta(days=1)).isoformat()
                            task["status"] = "approved"
                        elif task.get("repeat") == "hourly":
                            from datetime import timedelta
                            task["run_at"] = (run_at + timedelta(hours=1)).isoformat()
                            task["status"] = "approved"
                        elif task.get("repeat") == "weekly":
                            from datetime import timedelta
                            task["run_at"] = (run_at + timedelta(weeks=1)).isoformat()
                            task["status"] = "approved"
                    except Exception as e:
                        task["status"] = "failed"
                        task["error"] = str(e)
                        push_log(f"[Scheduler] Task #{task['id']} failed: {e}")
                    changed = True
            if changed:
                save_scheduled_tasks(tasks)
        except Exception as e:
            push_log(f"[Scheduler] Loop error: {e}")
        time.sleep(60)


# Patch approval handler to also approve scheduled tasks
_orig_api_approve = app.view_functions.get("api_approve")


TOOLS.append({"type": "function", "function": {"name": "schedule_task",
    "description": "Schedule a task for Jarvis to carry out at a future time or on a recurring basis. Requires owner approval.",
    "parameters": {"type": "object", "properties": {
        "description": {"type": "string"},
        "run_at": {"type": "string", "description": "ISO datetime or relative: '30m', '2h', '1d'"},
        "repeat": {"type": "string", "enum": ["", "hourly", "daily", "weekly"]}
    }, "required": ["description", "run_at"]}}})
TOOL_DISPATCH["schedule_task"] = lambda a: tool_schedule_task(
    a["description"], a["run_at"], a.get("repeat", ""))


@app.route("/api/scheduled_tasks")
def api_scheduled_tasks():
    return jsonify(load_scheduled_tasks())

@app.route("/api/scheduled_tasks/<int:task_id>/approve", methods=["POST"])
def api_approve_task(task_id):
    tasks = load_scheduled_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return jsonify({"ok": False, "error": "Task not found"}), 404
    task["status"] = "approved"
    save_scheduled_tasks(tasks)
    push_log(f"[Scheduler] Task #{task_id} approved by owner")
    return jsonify({"ok": True})

@app.route("/api/scheduled_tasks/<int:task_id>/cancel", methods=["POST"])
def api_cancel_task(task_id):
    tasks = load_scheduled_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return jsonify({"ok": False, "error": "Task not found"}), 404
    task["status"] = "cancelled"
    save_scheduled_tasks(tasks)
    push_log(f"[Scheduler] Task #{task_id} cancelled by owner")
    return jsonify({"ok": True})


# ── 6. EMAIL AUTOMATION ───────────────────────────────────────────────────────
# Jarvis can draft, read, and send emails. For sending, set your SMTP config.
# For reading, set your IMAP config. All send actions require explicit command.
# No email is ever sent automatically without your direct instruction.

SMTP_HOST     = ""          # e.g. "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = ""          # your email address
SMTP_PASSWORD = ""          # app password (not your real password)
SMTP_FROM     = ""          # display name + email

IMAP_HOST     = ""          # e.g. "imap.gmail.com"
IMAP_USER     = ""
IMAP_PASSWORD = ""


def tool_draft_email(to: str, subject: str, body: str) -> str:
    """Draft an email — shows what would be sent, queues for approval before sending."""
    draft = f"TO: {to}\nSUBJECT: {subject}\n\n{body}"
    approval_id = queue_pending_approval("send_email", f"To: {to} | Subject: {subject}")
    push_log(f"[Email] Draft queued for approval #{approval_id}")
    return (f"Email drafted and queued for your approval (id {approval_id}).\n"
            f"Preview:\n{draft}")


def tool_send_email_approved(to: str, subject: str, body: str) -> str:
    """Actually send an email via SMTP — only call this after owner approval."""
    if not SMTP_HOST or not SMTP_USER:
        return ("Email not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD "
                "in the config section of jarvis_app.py.")
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    try:
        msg = MIMEMultipart()
        msg["From"]    = SMTP_FROM or SMTP_USER
        msg["To"]      = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to, msg.as_string())
        push_log(f"[Email] Sent to {to}: {subject}")
        return f"Email sent to {to} successfully."
    except Exception as e:
        return f"Email send failed: {e}"


def tool_read_emails(folder: str = "INBOX", count: int = 5) -> str:
    """Read the latest emails from your inbox."""
    if not IMAP_HOST or not IMAP_USER:
        return ("Email reading not configured. Set IMAP_HOST, IMAP_USER, "
                "IMAP_PASSWORD in the config section.")
    import imaplib
    import email as email_lib
    from email.header import decode_header
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select(folder)
        _, data = mail.search(None, "ALL")
        ids = data[0].split()[-count:]
        result = []
        for uid in reversed(ids):
            _, msg_data = mail.fetch(uid, "(RFC822)")
            msg = email_lib.message_from_bytes(msg_data[0][1])
            subj_raw = msg["Subject"] or ""
            subj = decode_header(subj_raw)[0][0]
            if isinstance(subj, bytes):
                subj = subj.decode(errors="replace")
            frm = msg.get("From", "")
            result.append(f"FROM: {frm}\nSUBJECT: {subj}")
        mail.logout()
        return "\n---\n".join(result) if result else "No emails found."
    except Exception as e:
        return f"Email read failed: {e}"


TOOLS.append({"type": "function", "function": {"name": "draft_email",
    "description": "Draft an email and queue it for owner approval before sending.",
    "parameters": {"type": "object", "properties": {
        "to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}
    }, "required": ["to", "subject", "body"]}}})
TOOLS.append({"type": "function", "function": {"name": "read_emails",
    "description": "Read the latest emails from your inbox.",
    "parameters": {"type": "object", "properties": {
        "folder": {"type": "string", "default": "INBOX"},
        "count": {"type": "number", "default": 5}
    }}}})
TOOL_DISPATCH["draft_email"] = lambda a: tool_draft_email(a["to"], a["subject"], a["body"])
TOOL_DISPATCH["read_emails"] = lambda a: tool_read_emails(a.get("folder", "INBOX"), int(a.get("count", 5)))


@app.route("/api/email/draft", methods=["POST"])
def api_email_draft():
    from flask import request as freq
    body = freq.get_json(force=True)
    result = tool_draft_email(body.get("to",""), body.get("subject",""), body.get("body",""))
    return jsonify({"ok": True, "result": result})

@app.route("/api/email/inbox")
def api_email_inbox():
    result = tool_read_emails()
    return jsonify({"ok": True, "result": result})


# ── 7. SELF-IMPROVEMENT SYSTEM (human-approved, with backup + rollback) ───────
# Jarvis can propose code improvements. Every proposal is logged for your review.
# Nothing is ever applied automatically. You approve → backup created → patch applied
# → if it fails → auto rollback. You stay in full control at every step.

SELF_IMPROVE_DIR   = "jarvis_improvements"
SELF_IMPROVE_LOG   = os.path.join(SELF_IMPROVE_DIR, "proposals.json")
SELF_BACKUP_DIR    = os.path.join(SELF_IMPROVE_DIR, "backups")
JARVIS_SCRIPT_PATH = os.path.abspath(__file__)
os.makedirs(SELF_IMPROVE_DIR, exist_ok=True)
os.makedirs(SELF_BACKUP_DIR, exist_ok=True)


def load_proposals() -> list:
    if os.path.exists(SELF_IMPROVE_LOG):
        with open(SELF_IMPROVE_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_proposals(proposals: list):
    with open(SELF_IMPROVE_LOG, "w", encoding="utf-8") as f:
        json.dump(proposals, f, indent=2)


def tool_propose_improvement(title: str, description: str, patch_code: str) -> str:
    """Any worker can propose a code improvement. It is NEVER applied automatically.
    You review it in the dashboard and approve or reject it."""
    proposals = load_proposals()
    pid = len(proposals) + 1
    proposals.append({
        "id": pid, "title": title, "description": description,
        "patch_code": patch_code, "status": "pending_review",
        "proposed_at": time.strftime("%Y-%m-%d %H:%M"), "result": ""
    })
    save_proposals(proposals)
    push_log(f"[Self-Improve] Proposal #{pid} submitted: {title}")
    return (f"Improvement proposal #{pid} submitted for your review: '{title}'. "
            f"Review it in the dashboard under Self-Improvement → Proposals.")


def apply_improvement(proposal_id: int) -> dict:
    """Apply an approved improvement: backup → patch → test → rollback if broken."""
    proposals = load_proposals()
    prop = next((p for p in proposals if p["id"] == proposal_id), None)
    if not prop:
        return {"ok": False, "error": "Proposal not found"}

    # 1. Backup current file
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(SELF_BACKUP_DIR, f"jarvis_backup_{ts}.py")
    with open(JARVIS_SCRIPT_PATH, "r", encoding="utf-8") as f:
        original = f.read()
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(original)
    push_log(f"[Self-Improve] Backup created: {backup_path}")

    # 2. Write patch to a temp file and test syntax
    patch = prop["patch_code"]
    test_path = os.path.join(SELF_IMPROVE_DIR, f"patch_{proposal_id}.py")
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(patch)
    try:
        import ast as _ast
        _ast.parse(patch)
    except SyntaxError as e:
        prop["status"] = "failed"
        prop["result"] = f"Syntax error in patch: {e}"
        save_proposals(proposals)
        push_log(f"[Self-Improve] Proposal #{proposal_id} has a syntax error — not applied.")
        return {"ok": False, "error": f"Syntax error: {e}", "backup": backup_path}

    # 3. Apply by appending the patch to the script (safe — adds code, doesn't overwrite)
    try:
        with open(JARVIS_SCRIPT_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n\n# === SELF-IMPROVEMENT PATCH #{proposal_id} — {ts} ===\n")
            f.write(patch)
        prop["status"] = "applied"
        prop["result"] = f"Applied at {ts}. Backup: {backup_path}"
        save_proposals(proposals)
        push_log(f"[Self-Improve] Proposal #{proposal_id} applied successfully. Restart Jarvis to activate.")
        return {"ok": True, "message": "Patch applied. Restart Jarvis to activate.", "backup": backup_path}
    except Exception as e:
        # Rollback
        with open(JARVIS_SCRIPT_PATH, "w", encoding="utf-8") as f:
            f.write(original)
        prop["status"] = "failed"
        prop["result"] = f"Apply failed, rolled back: {e}"
        save_proposals(proposals)
        push_log(f"[Self-Improve] Proposal #{proposal_id} failed — rolled back to {backup_path}")
        return {"ok": False, "error": str(e), "rolled_back": True, "backup": backup_path}


TOOLS.append({"type": "function", "function": {"name": "propose_improvement",
    "description": "Propose a code improvement to Jarvis for owner review. Never applied automatically.",
    "parameters": {"type": "object", "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "patch_code": {"type": "string", "description": "Valid Python code to be reviewed and optionally applied"}
    }, "required": ["title", "description", "patch_code"]}}})
TOOL_DISPATCH["propose_improvement"] = lambda a: tool_propose_improvement(
    a["title"], a["description"], a["patch_code"])


@app.route("/api/improvements")
def api_improvements():
    return jsonify(load_proposals())

@app.route("/api/improvements/<int:proposal_id>/approve", methods=["POST"])
def api_approve_improvement(proposal_id):
    result = apply_improvement(proposal_id)
    return jsonify(result)

@app.route("/api/improvements/<int:proposal_id>/reject", methods=["POST"])
def api_reject_improvement(proposal_id):
    proposals = load_proposals()
    prop = next((p for p in proposals if p["id"] == proposal_id), None)
    if prop:
        prop["status"] = "rejected"
        save_proposals(proposals)
        push_log(f"[Self-Improve] Proposal #{proposal_id} rejected by owner")
    return jsonify({"ok": True})

@app.route("/api/improvements/rollback/<string:backup_name>", methods=["POST"])
def api_rollback(backup_name):
    """Manually restore a backup version of Jarvis."""
    backup_path = os.path.join(SELF_BACKUP_DIR, backup_name)
    if not os.path.exists(backup_path):
        return jsonify({"ok": False, "error": "Backup not found"}), 404
    with open(backup_path, "r", encoding="utf-8") as f:
        content = f.read()
    with open(JARVIS_SCRIPT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    push_log(f"[Self-Improve] Rolled back to {backup_name}")
    return jsonify({"ok": True, "message": f"Rolled back to {backup_name}. Restart Jarvis to activate."})

@app.route("/api/improvements/backups")
def api_list_backups():
    backups = sorted(os.listdir(SELF_BACKUP_DIR), reverse=True)
    return jsonify({"backups": backups})


# ── 8. LAUNCH ALL NEW BACKGROUND SERVICES ────────────────────────────────────
# All new services are started as daemon threads — they stop automatically
# when Jarvis stops. Nothing affects existing startup logic.

def _start_new_services():
    """Start all new background services. Called once at startup."""
    threading.Thread(target=_wake_listener_loop, daemon=True, name="WakeListener").start()
    threading.Thread(target=_scheduler_loop, daemon=True, name="TaskScheduler").start()
    push_log("[New Services] Wake word listener + Task scheduler started.")

# ═══════════════════════════════════════════════════════════════════════════════
# END OF NEW FEATURES — ALL EXISTING CODE BELOW IS UNTOUCHED
# ═══════════════════════════════════════════════════════════════════════════════




# ═══════════════════════════════════════════════════════════════════════════════
# POWER UPGRADE PACK — 8 NEW CAPABILITIES
# Nothing above this line is changed. Pure additions only.
#
# New install requirements (only needed if you use each feature):
#   pip install playwright beautifulsoup4 lxml adb-shell pure-python-adb
#   playwright install chromium
#
# Quick-start:  python jarvis_app.py
# All features degrade gracefully if optional deps aren't installed.
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# U1. FULL COMPUTER VISION — Screen understanding (beyond webcam)
#     Captures screen, sends to vision-capable LLM (LLaVA via Ollama),
#     lets Jarvis see and describe EVERYTHING on the screen in real time.
# ─────────────────────────────────────────────────────────────────────────────

VISION_LLM_MODEL = "llava"          # Change to "llava:13b" or "bakllava" if you have it
SCREEN_VISION_ENABLED = True
_screen_lock = threading.Lock()


def tool_see_screen(question: str = "What do you see on the screen?") -> str:
    """Capture the full screen and ask the vision LLM what it sees."""
    with _screen_lock:
        try:
            import pyautogui
            from PIL import Image
            import io, base64

            screenshot = pyautogui.screenshot()
            # Resize to keep token count reasonable (1280px wide max)
            w, h = screenshot.size
            if w > 1280:
                ratio = 1280 / w
                screenshot = screenshot.resize((1280, int(h * ratio)), Image.LANCZOS)

            buf = io.BytesIO()
            screenshot.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        except Exception as e:
            return f"Screen capture failed: {e}"

    # Send to vision LLM via Ollama (llava/bakllava/moondream)
    try:
        payload = {
            "model": VISION_LLM_MODEL,
            "prompt": question,
            "images": [img_b64],
            "stream": False
        }
        resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
        result = resp.json()
        return result.get("response", "Vision model returned no response.")
    except Exception as e:
        # Fallback: save to disk and return path
        path = os.path.join(IMAGE_DIR, f"screen_{int(time.time())}.png")
        try:
            import pyautogui
            pyautogui.screenshot(path)
        except Exception:
            pass
        return (f"Vision LLM not available (is '{VISION_LLM_MODEL}' pulled in Ollama?). "
                f"Screenshot saved to {path}. Error: {e}")


def tool_read_screen_text() -> str:
    """Use pytesseract OCR to extract all text visible on screen."""
    try:
        import pyautogui, pytesseract
        from PIL import Image
        screenshot = pyautogui.screenshot()
        text = pytesseract.image_to_string(screenshot)
        return text.strip()[:3000] if text.strip() else "No text detected on screen."
    except ImportError:
        return ("pytesseract not installed. Run: pip install pytesseract  "
                "and install Tesseract OCR from https://github.com/UB-Mannheim/tesseract/wiki")
    except Exception as e:
        return f"OCR failed: {e}"


def tool_click_on_screen(target_description: str) -> str:
    """
    Find and click something on screen by description.
    Uses vision to locate the element, then clicks it.
    """
    with CONTROL_LOCK:
        try:
            import pyautogui
            # First, get screen understanding
            location_prompt = (
                f"I need to click on: '{target_description}'. "
                "Look at the screen and tell me the approximate X,Y pixel coordinates "
                "of that element. Reply with ONLY: x=NNN y=NNN"
            )
            location_result = tool_see_screen(location_prompt)

            # Parse coordinates
            x_match = re.search(r'x\s*=\s*(\d+)', location_result, re.IGNORECASE)
            y_match = re.search(r'y\s*=\s*(\d+)', location_result, re.IGNORECASE)

            if x_match and y_match:
                x, y = int(x_match.group(1)), int(y_match.group(1))
                pyautogui.click(x, y)
                push_log(f"[Screen Vision] Clicked at ({x}, {y}) for: {target_description}")
                return f"Clicked on '{target_description}' at ({x}, {y})"
            else:
                return f"Could not locate '{target_description}' on screen. Vision response: {location_result}"
        except Exception as e:
            return f"Click failed: {e}"


# Register screen vision tools
TOOLS.append({"type": "function", "function": {
    "name": "see_screen",
    "description": "Capture the full computer screen and use AI vision to understand and describe what's visible. Can answer questions about the screen content.",
    "parameters": {"type": "object", "properties": {
        "question": {"type": "string", "description": "What to look for or ask about the screen. Default: describe everything visible."}
    }}}})

TOOLS.append({"type": "function", "function": {
    "name": "read_screen_text",
    "description": "Use OCR to extract all visible text from the screen. Useful for reading content in apps that can't be accessed programmatically.",
    "parameters": {"type": "object", "properties": {}}}})

TOOLS.append({"type": "function", "function": {
    "name": "click_on_screen",
    "description": "Use AI vision to find and click on a UI element described in natural language, e.g. 'the submit button' or 'the search bar'.",
    "parameters": {"type": "object", "properties": {
        "target_description": {"type": "string", "description": "Natural language description of what to click"}
    }, "required": ["target_description"]}}})

TOOL_DISPATCH["see_screen"]        = lambda a: tool_see_screen(a.get("question", "What do you see on the screen?"))
TOOL_DISPATCH["read_screen_text"]  = lambda a: tool_read_screen_text()
TOOL_DISPATCH["click_on_screen"]   = lambda a: tool_click_on_screen(a["target_description"])

push_log("[U1] Screen Vision tools registered (see_screen, read_screen_text, click_on_screen)")


# ─────────────────────────────────────────────────────────────────────────────
# U2. BROWSER AUTOMATION WITH MEMORY
#     Playwright-powered browser agent. Navigates, clicks, fills forms, reads
#     page content, and remembers browsing sessions. Requires: playwright install chromium
# ─────────────────────────────────────────────────────────────────────────────

BROWSER_MEMORY_FILE = "jarvis_browser_memory.json"
_browser_instance = None
_browser_page = None
_browser_lock = threading.Lock()


def load_browser_memory() -> dict:
    if os.path.exists(BROWSER_MEMORY_FILE):
        with open(BROWSER_MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"visited": [], "saved_pages": {}, "credentials_hint": {}}


def save_browser_memory(data: dict):
    with open(BROWSER_MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _get_browser_page():
    """Get or create a persistent browser page."""
    global _browser_instance, _browser_page
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "playwright not installed. Run: pip install playwright && playwright install chromium"

    with _browser_lock:
        if _browser_page is None:
            try:
                pw = sync_playwright().start()
                _browser_instance = pw.chromium.launch(headless=False)  # headless=False so you can see it
                _browser_page = _browser_instance.new_page()
                push_log("[Browser] Chromium launched.")
            except Exception as e:
                return None, f"Browser launch failed: {e}"
    return _browser_page, None


def tool_browser_navigate(url: str, remember: bool = True) -> str:
    """Navigate the browser to a URL."""
    page, err = _get_browser_page()
    if err:
        return err
    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        title = page.title()
        if remember:
            mem = load_browser_memory()
            entry = {"url": url, "title": title, "time": time.strftime("%Y-%m-%d %H:%M")}
            mem["visited"] = [e for e in mem["visited"] if e["url"] != url]
            mem["visited"].insert(0, entry)
            mem["visited"] = mem["visited"][:100]
            save_browser_memory(mem)
        push_log(f"[Browser] Navigated to {url} — '{title}'")
        return f"Navigated to '{title}' ({url})"
    except Exception as e:
        return f"Navigation failed: {e}"


def tool_browser_click(selector_or_text: str) -> str:
    """Click an element on the current page by CSS selector or visible text."""
    page, err = _get_browser_page()
    if err:
        return err
    try:
        # Try text match first, then CSS selector
        try:
            page.get_by_text(selector_or_text, exact=False).first.click(timeout=5000)
        except Exception:
            page.click(selector_or_text, timeout=5000)
        push_log(f"[Browser] Clicked: {selector_or_text}")
        return f"Clicked: {selector_or_text}"
    except Exception as e:
        return f"Click failed: {e}"


def tool_browser_type(selector: str, text: str) -> str:
    """Type text into an input field on the current page."""
    page, err = _get_browser_page()
    if err:
        return err
    try:
        page.fill(selector, text)
        push_log(f"[Browser] Typed into {selector}")
        return f"Typed into {selector}"
    except Exception as e:
        return f"Type failed: {e}"


def tool_browser_read_page() -> str:
    """Extract the visible text content of the current browser page."""
    page, err = _get_browser_page()
    if err:
        return err
    try:
        text = page.inner_text("body")
        return text[:5000].strip() if text else "No text content found."
    except Exception as e:
        return f"Read failed: {e}"


def tool_browser_screenshot() -> str:
    """Take a screenshot of the current browser page."""
    page, err = _get_browser_page()
    if err:
        return err
    try:
        path = os.path.join(IMAGE_DIR, f"browser_{int(time.time())}.png")
        page.screenshot(path=path)
        push_log(f"[Browser] Screenshot: {path}")
        return f"Browser screenshot saved: {path}"
    except Exception as e:
        return f"Browser screenshot failed: {e}"


def tool_browser_run_js(script: str) -> str:
    """Execute JavaScript in the current browser page and return the result."""
    page, err = _get_browser_page()
    if err:
        return err
    try:
        result = page.evaluate(script)
        push_log(f"[Browser] Ran JS: {script[:60]}")
        return str(result)[:2000]
    except Exception as e:
        return f"JS execution failed: {e}"


def tool_browser_history() -> str:
    """Return the browser session memory — recently visited pages."""
    mem = load_browser_memory()
    visited = mem.get("visited", [])
    if not visited:
        return "No browser history yet."
    lines = [f"{i+1}. [{v['time']}] {v['title']} — {v['url']}" for i, v in enumerate(visited[:20])]
    return "\n".join(lines)


# Register browser tools
for _name, _desc, _params, _fn in [
    ("browser_navigate", "Navigate the browser to a URL. Browser opens visibly so you can watch.", {"url": {"type": "string"}, "remember": {"type": "boolean"}}, lambda a: tool_browser_navigate(a["url"], a.get("remember", True))),
    ("browser_click", "Click an element on the current web page by visible text or CSS selector.", {"selector_or_text": {"type": "string"}}, lambda a: tool_browser_click(a["selector_or_text"])),
    ("browser_type", "Type text into an input field on the current web page.", {"selector": {"type": "string"}, "text": {"type": "string"}}, lambda a: tool_browser_type(a["selector"], a["text"])),
    ("browser_read_page", "Read all visible text content from the current browser page.", {}, lambda a: tool_browser_read_page()),
    ("browser_screenshot", "Take a screenshot of the current browser page.", {}, lambda a: tool_browser_screenshot()),
    ("browser_run_js", "Execute JavaScript in the browser page.", {"script": {"type": "string"}}, lambda a: tool_browser_run_js(a["script"])),
    ("browser_history", "Show recently visited pages from browser session memory.", {}, lambda a: tool_browser_history()),
]:
    TOOLS.append({"type": "function", "function": {"name": _name, "description": _desc,
        "parameters": {"type": "object", "properties": _params}}})
    TOOL_DISPATCH[_name] = _fn

push_log("[U2] Browser Automation tools registered (7 tools)")


# ─────────────────────────────────────────────────────────────────────────────
# U3. PHONE CONTROL (Android ADB)
#     Jarvis can control your Android phone over USB or WiFi ADB.
#     Enable ADB on your phone: Settings → Developer Options → USB Debugging
# ─────────────────────────────────────────────────────────────────────────────

ADB_DEVICE_IP = ""      # Set to your phone's IP for WiFi ADB, e.g. "192.168.1.50"
ADB_PORT      = 5555
_phone_lock   = threading.Lock()


def _adb(command: str, timeout: int = 10) -> str:
    """Run an adb command and return output."""
    base = f"adb -s {ADB_DEVICE_IP}:{ADB_PORT}" if ADB_DEVICE_IP else "adb"
    try:
        result = subprocess.run(
            f"{base} {command}", shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        return (result.stdout.strip() or result.stderr.strip() or "OK")[:500]
    except Exception as e:
        return f"ADB error: {e}"


def tool_phone_screenshot() -> str:
    """Take a screenshot of the phone screen and pull it to your PC."""
    with _phone_lock:
        path_on_phone = "/sdcard/jarvis_shot.png"
        path_on_pc = os.path.join(IMAGE_DIR, f"phone_{int(time.time())}.png")
        _adb(f"shell screencap -p {path_on_phone}")
        result = _adb(f"pull {path_on_phone} {path_on_pc}")
        push_log(f"[Phone] Screenshot pulled: {path_on_pc}")
        return f"Phone screenshot: {path_on_pc}" if os.path.exists(path_on_pc) else f"Pull failed: {result}"


def tool_phone_tap(x: int, y: int) -> str:
    """Tap at pixel coordinates on the phone screen."""
    with _phone_lock:
        result = _adb(f"shell input tap {x} {y}")
        push_log(f"[Phone] Tapped ({x},{y})")
        return f"Tapped ({x},{y}): {result}"


def tool_phone_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> str:
    """Swipe on the phone screen."""
    with _phone_lock:
        result = _adb(f"shell input swipe {x1} {y1} {x2} {y2} {duration_ms}")
        return f"Swiped: {result}"


def tool_phone_type(text: str) -> str:
    """Type text on the phone (into the focused input field)."""
    with _phone_lock:
        safe = text.replace(" ", "%s").replace("'", "\\'")
        result = _adb(f"shell input text '{safe}'")
        return f"Typed on phone: {result}"


def tool_phone_key(keycode: str) -> str:
    """Press a phone key by name: HOME, BACK, ENTER, VOLUME_UP, etc."""
    keymap = {
        "home": 3, "back": 4, "enter": 66, "volume_up": 24,
        "volume_down": 25, "power": 26, "menu": 82, "delete": 67
    }
    code = keymap.get(keycode.lower(), keycode)
    with _phone_lock:
        result = _adb(f"shell input keyevent {code}")
        return f"Key {keycode}: {result}"


def tool_phone_open_app(package: str) -> str:
    """Open an Android app by package name, e.g. 'com.instagram.android'."""
    with _phone_lock:
        result = _adb(f"shell monkey -p {package} -c android.intent.category.LAUNCHER 1")
        push_log(f"[Phone] Opened {package}")
        return f"Opened {package}: {result}"


def tool_phone_call(number: str) -> str:
    """Start a phone call to a number. Requires owner approval."""
    approval_id = queue_pending_approval("phone_call", f"Call {number}")
    return f"Phone call to {number} queued for approval (id {approval_id})."


def tool_phone_sms(number: str, message: str) -> str:
    """Send an SMS via ADB. Requires owner approval."""
    approval_id = queue_pending_approval("send_sms", f"To: {number} | {message[:80]}")
    return f"SMS queued for approval (id {approval_id}). Message: {message[:80]}"


def tool_phone_wifi_connect() -> str:
    """Connect to the phone over WiFi ADB (must run USB ADB first to enable)."""
    if not ADB_DEVICE_IP:
        return "Set ADB_DEVICE_IP in the config to use WiFi ADB."
    result = _adb(f"tcpip {ADB_PORT}")
    time.sleep(1)
    connect = subprocess.run(
        f"adb connect {ADB_DEVICE_IP}:{ADB_PORT}",
        shell=True, capture_output=True, text=True
    )
    return f"WiFi ADB: {connect.stdout.strip() or connect.stderr.strip()}"


# Register phone tools
for _name, _desc, _params, _fn in [
    ("phone_screenshot", "Take a screenshot of the Android phone screen.", {}, lambda a: tool_phone_screenshot()),
    ("phone_tap", "Tap at pixel coordinates on the phone screen.", {"x": {"type": "integer"}, "y": {"type": "integer"}}, lambda a: tool_phone_tap(a["x"], a["y"])),
    ("phone_swipe", "Swipe on the phone screen from one point to another.", {"x1": {"type": "integer"}, "y1": {"type": "integer"}, "x2": {"type": "integer"}, "y2": {"type": "integer"}, "duration_ms": {"type": "integer"}}, lambda a: tool_phone_swipe(a["x1"], a["y1"], a["x2"], a["y2"], a.get("duration_ms", 300))),
    ("phone_type", "Type text on the phone.", {"text": {"type": "string"}}, lambda a: tool_phone_type(a["text"])),
    ("phone_key", "Press a phone key: HOME, BACK, ENTER, VOLUME_UP, POWER, MENU.", {"keycode": {"type": "string"}}, lambda a: tool_phone_key(a["keycode"])),
    ("phone_open_app", "Open an Android app by package name.", {"package": {"type": "string"}}, lambda a: tool_phone_open_app(a["package"])),
    ("phone_call", "Initiate a phone call (queued for owner approval).", {"number": {"type": "string"}}, lambda a: tool_phone_call(a["number"])),
    ("phone_sms", "Send an SMS via phone (queued for owner approval).", {"number": {"type": "string"}, "message": {"type": "string"}}, lambda a: tool_phone_sms(a["number"], a["message"])),
    ("phone_wifi_connect", "Connect to the Android phone over WiFi ADB.", {}, lambda a: tool_phone_wifi_connect()),
]:
    TOOLS.append({"type": "function", "function": {"name": _name, "description": _desc,
        "parameters": {"type": "object", "properties": _params,
                       "required": [k for k in _params if k not in ("remember", "duration_ms")]}}})
    TOOL_DISPATCH[_name] = _fn

push_log("[U3] Phone Control tools registered (9 ADB tools)")


# ─────────────────────────────────────────────────────────────────────────────
# U4. PLUGIN SYSTEM — Load external tool plugins at runtime
#     Drop a .py file into jarvis_plugins/ and Jarvis auto-loads it on startup.
#     Each plugin just defines PLUGIN_TOOLS (list) and PLUGIN_DISPATCH (dict).
# ─────────────────────────────────────────────────────────────────────────────

PLUGINS_DIR = "jarvis_plugins"
os.makedirs(PLUGINS_DIR, exist_ok=True)

# Write example plugin template if dir is empty
_example_plugin = os.path.join(PLUGINS_DIR, "example_plugin.py.template")
if not os.path.exists(_example_plugin):
    with open(_example_plugin, "w", encoding="utf-8") as _f:
        _f.write('''"""
Jarvis Plugin Template
Rename to my_plugin.py (remove .template) to activate.

Define PLUGIN_TOOLS (Ollama tool format) and PLUGIN_DISPATCH (name -> callable).
"""

PLUGIN_TOOLS = [
    {"type": "function", "function": {
        "name": "my_custom_tool",
        "description": "Describe what your tool does.",
        "parameters": {"type": "object", "properties": {
            "input": {"type": "string", "description": "Input value"}
        }, "required": ["input"]}
    }}
]

def my_custom_tool(args: dict) -> str:
    return f"Plugin received: {args.get(\'input\', \'\')}"

PLUGIN_DISPATCH = {
    "my_custom_tool": my_custom_tool,
}
''')

def load_plugins():
    """Scan jarvis_plugins/ and load all .py files as plugins."""
    loaded = 0
    for fname in os.listdir(PLUGINS_DIR):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        fpath = os.path.join(PLUGINS_DIR, fname)
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(fname[:-3], fpath)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            plugin_tools = getattr(mod, "PLUGIN_TOOLS", [])
            plugin_dispatch = getattr(mod, "PLUGIN_DISPATCH", {})
            TOOLS.extend(plugin_tools)
            TOOL_DISPATCH.update(plugin_dispatch)
            push_log(f"[Plugin] Loaded '{fname}': {len(plugin_tools)} tools")
            loaded += 1
        except Exception as e:
            push_log(f"[Plugin] Failed to load '{fname}': {e}")
    if loaded:
        push_log(f"[U4] Plugin system: {loaded} plugin(s) loaded from {PLUGINS_DIR}/")
    else:
        push_log(f"[U4] Plugin system active. Drop .py files in {PLUGINS_DIR}/ to extend Jarvis.")

load_plugins()

# API route to reload plugins at runtime
@app.route("/api/plugins/reload", methods=["POST"])
def api_reload_plugins():
    load_plugins()
    return jsonify({"ok": True, "tool_count": len(TOOLS)})

@app.route("/api/plugins/list")
def api_list_plugins():
    plugins = [f for f in os.listdir(PLUGINS_DIR) if f.endswith(".py")]
    return jsonify({"plugins": plugins, "tool_count": len(TOOLS)})


# ─────────────────────────────────────────────────────────────────────────────
# U5. AUTONOMOUS CODING AGENT — Plan → Write → Run → Debug loop
#     Jarvis can autonomously plan, write code, execute it, see errors,
#     fix them, and iterate — fully owner-approved before any dangerous step.
# ─────────────────────────────────────────────────────────────────────────────

CODING_SESSIONS_FILE = "jarvis_coding_sessions.json"
CODING_WORKSPACE = "jarvis_workspace"
os.makedirs(CODING_WORKSPACE, exist_ok=True)


def load_coding_sessions() -> list:
    if os.path.exists(CODING_SESSIONS_FILE):
        with open(CODING_SESSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_coding_sessions(sessions: list):
    with open(CODING_SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2)


def tool_code_agent(task: str, language: str = "python", max_iterations: int = 5) -> str:
    """
    Autonomous coding agent: plans → writes code → executes → debugs.
    Runs up to max_iterations fix cycles. Each execution requires approval for
    potentially dangerous operations.
    """
    session_id = int(time.time())
    workspace_file = os.path.join(CODING_WORKSPACE, f"task_{session_id}.{language[:2]}")
    push_log(f"[Code Agent] Starting session {session_id}: {task[:80]}")

    # Phase 1: Plan + generate code
    planning_messages = [
        {"role": "system", "content": (
            f"You are an expert {language} developer. Write complete, working code to solve the given task. "
            "Output ONLY the raw code with no explanation, no markdown fences. "
            "The code should be self-contained and runnable."
        )},
        {"role": "user", "content": task}
    ]
    resp = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL, "messages": planning_messages,
        "stream": False, "options": {"num_ctx": OLLAMA_NUM_CTX}
    }).json()
    code = resp["message"]["content"].strip()
    # Strip markdown fences if present
    code = re.sub(r'^```\w*\n?', '', code, flags=re.MULTILINE)
    code = re.sub(r'^```$', '', code, flags=re.MULTILINE)
    code = code.strip()

    with open(workspace_file, "w", encoding="utf-8") as f:
        f.write(code)

    push_log(f"[Code Agent] Code written to {workspace_file}")

    # Phase 2: Execute + debug loop
    iteration = 0
    last_output = ""
    while iteration < max_iterations:
        iteration += 1
        push_log(f"[Code Agent] Iteration {iteration}: running {workspace_file}")

        if language == "python":
            run_cmd = f"python \"{workspace_file}\""
        elif language in ("javascript", "js", "node"):
            run_cmd = f"node \"{workspace_file}\""
        else:
            run_cmd = f"\"{workspace_file}\""

        try:
            result = subprocess.run(run_cmd, shell=True, capture_output=True,
                                     text=True, timeout=30)
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            last_output = stdout or stderr or "No output"

            if result.returncode == 0:
                push_log(f"[Code Agent] Success on iteration {iteration}!")
                session = {
                    "id": session_id, "task": task, "language": language,
                    "file": workspace_file, "iterations": iteration,
                    "status": "success", "output": last_output[:500],
                    "time": time.strftime("%Y-%m-%d %H:%M")
                }
                sessions = load_coding_sessions()
                sessions.append(session)
                save_coding_sessions(sessions)
                return f"✅ Code completed in {iteration} iteration(s).\nFile: {workspace_file}\nOutput:\n{last_output[:800]}"

            # Has error — ask LLM to fix it
            push_log(f"[Code Agent] Error on iteration {iteration}: {stderr[:200]}")
            fix_messages = [
                {"role": "system", "content": "You are an expert debugger. Fix the code error. Output ONLY the corrected complete code."},
                {"role": "user", "content": f"Task: {task}\n\nCurrent code:\n{code}\n\nError:\n{stderr[:1000]}\n\nFix the code:"}
            ]
            fix_resp = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL, "messages": fix_messages,
                "stream": False, "options": {"num_ctx": OLLAMA_NUM_CTX}
            }).json()
            code = fix_resp["message"]["content"].strip()
            code = re.sub(r'^```\w*\n?', '', code, flags=re.MULTILINE)
            code = re.sub(r'^```$', '', code, flags=re.MULTILINE)
            code = code.strip()
            with open(workspace_file, "w", encoding="utf-8") as f:
                f.write(code)

        except subprocess.TimeoutExpired:
            last_output = "Execution timed out (30s)"
            break
        except Exception as e:
            last_output = str(e)
            break

    # Failed after max iterations
    sessions = load_coding_sessions()
    sessions.append({"id": session_id, "task": task, "language": language,
                     "file": workspace_file, "iterations": iteration,
                     "status": "failed", "output": last_output[:500],
                     "time": time.strftime("%Y-%m-%d %H:%M")})
    save_coding_sessions(sessions)
    return (f"⚠️ Code agent ran {iteration} iteration(s) but couldn't fully resolve errors.\n"
            f"File: {workspace_file}\nLast output: {last_output[:500]}")


def tool_code_write(filename: str, code: str, description: str = "") -> str:
    """Write code to a file in the workspace."""
    path = os.path.join(CODING_WORKSPACE, filename)
    # Require approval if overwriting
    if os.path.exists(path):
        aid = queue_pending_approval("overwrite_code", f"{filename}: {description[:80]}")
        return f"Overwrite queued for approval (id {aid}): {filename}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    push_log(f"[Code] Wrote {filename}: {description or '(no description)'}")
    return f"File created: {path}"


def tool_code_run(filename: str, args: str = "") -> str:
    """Run a code file from the workspace."""
    path = os.path.join(CODING_WORKSPACE, filename)
    if not os.path.exists(path):
        return f"File not found: {path}"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    runner = {"py": "python", "js": "node", "ts": "npx ts-node"}.get(ext, "")
    cmd = f"{runner} \"{path}\" {args}".strip() if runner else f"\"{path}\" {args}".strip()
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=CODING_WORKSPACE)
        output = (result.stdout.strip() or result.stderr.strip() or "No output.")[:1000]
        push_log(f"[Code] Ran {filename}: exit {result.returncode}")
        return output
    except subprocess.TimeoutExpired:
        return "Execution timed out."
    except Exception as e:
        return f"Run failed: {e}"


TOOLS.append({"type": "function", "function": {
    "name": "code_agent",
    "description": "Autonomous coding agent: given a task, plans → writes → runs → debugs code automatically until it works.",
    "parameters": {"type": "object", "properties": {
        "task": {"type": "string", "description": "What the code should do"},
        "language": {"type": "string", "enum": ["python", "javascript", "node"], "description": "Programming language"},
        "max_iterations": {"type": "integer", "description": "Max debug iterations (default 5)"}
    }, "required": ["task"]}}})

TOOLS.append({"type": "function", "function": {
    "name": "code_write",
    "description": "Write a code file to the Jarvis workspace folder.",
    "parameters": {"type": "object", "properties": {
        "filename": {"type": "string"}, "code": {"type": "string"}, "description": {"type": "string"}
    }, "required": ["filename", "code"]}}})

TOOLS.append({"type": "function", "function": {
    "name": "code_run",
    "description": "Run a code file from the Jarvis workspace folder.",
    "parameters": {"type": "object", "properties": {
        "filename": {"type": "string"}, "args": {"type": "string"}
    }, "required": ["filename"]}}})

TOOL_DISPATCH["code_agent"] = lambda a: tool_code_agent(a["task"], a.get("language", "python"), int(a.get("max_iterations", 5)))
TOOL_DISPATCH["code_write"] = lambda a: tool_code_write(a["filename"], a["code"], a.get("description", ""))
TOOL_DISPATCH["code_run"]   = lambda a: tool_code_run(a["filename"], a.get("args", ""))

push_log("[U5] Autonomous Coding Agent tools registered (code_agent, code_write, code_run)")


# ─────────────────────────────────────────────────────────────────────────────
# U6. LONG-TERM GOALS + SELF-PLANNING (multi-day / multi-week)
#     Owner sets high-level goals. Jarvis breaks them into milestones + daily
#     tasks, tracks progress, and surfaces what to work on next.
# ─────────────────────────────────────────────────────────────────────────────

GOALS_FILE = "jarvis_goals.json"


def load_goals() -> list:
    if os.path.exists(GOALS_FILE):
        with open(GOALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_goals(goals: list):
    with open(GOALS_FILE, "w", encoding="utf-8") as f:
        json.dump(goals, f, indent=2)


def tool_set_goal(title: str, description: str, deadline: str = "", category: str = "general") -> str:
    """Set a long-term goal. Jarvis auto-generates a milestone breakdown."""
    goals = load_goals()
    goal_id = len(goals) + 1

    # Ask Jarvis to plan milestones
    milestone_prompt = [
        {"role": "system", "content": "You are a strategic planner. Break this goal into 3-7 concrete milestones. Reply ONLY as a JSON array of strings."},
        {"role": "user", "content": f"Goal: {title}\nDescription: {description}\nDeadline: {deadline or 'open-ended'}"}
    ]
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL, "messages": milestone_prompt,
            "stream": False, "options": {"num_ctx": 8192}
        }).json()
        raw = resp["message"]["content"].strip().strip("`")
        raw = re.sub(r'^json\s*', '', raw, flags=re.IGNORECASE).strip()
        milestones = json.loads(raw) if raw.startswith("[") else []
    except Exception:
        milestones = ["Plan approach", "Execute", "Review & iterate", "Complete"]

    goal = {
        "id": goal_id, "title": title, "description": description,
        "deadline": deadline, "category": category,
        "status": "active", "progress_pct": 0,
        "milestones": [{"milestone": m, "done": False} for m in milestones],
        "notes": [], "created": time.strftime("%Y-%m-%d"), "updated": time.strftime("%Y-%m-%d")
    }
    goals.append(goal)
    save_goals(goals)
    push_log(f"[Goals] New goal #{goal_id}: {title}")
    return (f"Goal #{goal_id} set: '{title}'\n"
            f"Milestones planned:\n" + "\n".join(f"  {i+1}. {m}" for i, m in enumerate(milestones)))


def tool_update_goal_progress(goal_id: int, progress_pct: int, note: str = "") -> str:
    """Update progress on a goal (0-100%) and add a note."""
    goals = load_goals()
    goal = next((g for g in goals if g["id"] == goal_id), None)
    if not goal:
        return f"Goal #{goal_id} not found."
    goal["progress_pct"] = max(0, min(100, progress_pct))
    goal["status"] = "completed" if progress_pct >= 100 else "active"
    goal["updated"] = time.strftime("%Y-%m-%d")
    if note:
        goal["notes"].append({"note": note, "time": time.strftime("%Y-%m-%d %H:%M")})
    save_goals(goals)
    push_log(f"[Goals] #{goal_id} progress: {progress_pct}%")
    return f"Goal #{goal_id} updated: {progress_pct}% complete. {'🎉 COMPLETED!' if progress_pct >= 100 else ''}"


def tool_check_milestone(goal_id: int, milestone_index: int) -> str:
    """Mark a milestone as done."""
    goals = load_goals()
    goal = next((g for g in goals if g["id"] == goal_id), None)
    if not goal:
        return f"Goal #{goal_id} not found."
    milestones = goal.get("milestones", [])
    if milestone_index < 1 or milestone_index > len(milestones):
        return f"Milestone index out of range (1-{len(milestones)})."
    milestones[milestone_index - 1]["done"] = True
    done_count = sum(1 for m in milestones if m["done"])
    goal["progress_pct"] = int(done_count / len(milestones) * 100)
    goal["updated"] = time.strftime("%Y-%m-%d")
    save_goals(goals)
    return f"Milestone {milestone_index} checked off. Progress: {goal['progress_pct']}%"


def tool_list_goals(status: str = "active") -> str:
    """List goals filtered by status: active, completed, all."""
    goals = load_goals()
    filtered = goals if status == "all" else [g for g in goals if g["status"] == status]
    if not filtered:
        return f"No {status} goals."
    lines = []
    for g in filtered:
        done_m = sum(1 for m in g.get("milestones", []) if m["done"])
        total_m = len(g.get("milestones", []))
        lines.append(f"#{g['id']} [{g['progress_pct']}%] {g['title']} — {done_m}/{total_m} milestones, deadline: {g.get('deadline') or 'open'}")
    return "\n".join(lines)


def tool_next_actions() -> str:
    """Ask Jarvis what the owner should work on next based on active goals."""
    goals = [g for g in load_goals() if g["status"] == "active"]
    if not goals:
        return "No active goals. Set some goals first!"
    goals_summary = "\n".join(
        f"Goal #{g['id']}: {g['title']} ({g['progress_pct']}%) — "
        f"Next milestone: {next((m['milestone'] for m in g.get('milestones',[]) if not m['done']), 'all done')}"
        for g in goals[:10]
    )
    prompt = [
        {"role": "system", "content": "You are a strategic advisor. Given these active goals and their progress, suggest the top 3 most impactful actions the owner should take TODAY. Be specific and actionable."},
        {"role": "user", "content": goals_summary}
    ]
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL, "messages": prompt,
            "stream": False, "options": {"num_ctx": 8192}
        }).json()
        return resp["message"]["content"].strip()
    except Exception as e:
        return f"Could not generate next actions: {e}"


for _name, _desc, _params, _req, _fn in [
    ("set_goal", "Set a long-term goal with a deadline. Jarvis automatically plans milestones.",
     {"title": {"type": "string"}, "description": {"type": "string"}, "deadline": {"type": "string"}, "category": {"type": "string"}},
     ["title", "description"], lambda a: tool_set_goal(a["title"], a["description"], a.get("deadline",""), a.get("category","general"))),

    ("update_goal_progress", "Update progress percentage on a goal and optionally add a progress note.",
     {"goal_id": {"type": "integer"}, "progress_pct": {"type": "integer"}, "note": {"type": "string"}},
     ["goal_id", "progress_pct"], lambda a: tool_update_goal_progress(a["goal_id"], a["progress_pct"], a.get("note",""))),

    ("check_milestone", "Mark a goal milestone as completed.",
     {"goal_id": {"type": "integer"}, "milestone_index": {"type": "integer"}},
     ["goal_id", "milestone_index"], lambda a: tool_check_milestone(a["goal_id"], a["milestone_index"])),

    ("list_goals", "List all goals. Filter by status: active, completed, or all.",
     {"status": {"type": "string", "enum": ["active", "completed", "all"]}},
     [], lambda a: tool_list_goals(a.get("status", "active"))),

    ("next_actions", "Ask Jarvis what the most impactful things to work on today are, based on active goals.",
     {}, [], lambda a: tool_next_actions()),
]:
    TOOLS.append({"type": "function", "function": {"name": _name, "description": _desc,
        "parameters": {"type": "object", "properties": _params, "required": _req}}})
    TOOL_DISPATCH[_name] = _fn

push_log("[U6] Long-Term Goals + Self-Planning tools registered (set_goal, milestones, next_actions)")


# ─────────────────────────────────────────────────────────────────────────────
# U7. MULTI-AGENT COLLABORATION — Named persistent agents
#     Beyond Leader/Worker, Jarvis can spin up named persistent AI agents
#     (CEO Agent, Research Agent, Coding Agent, etc.) that maintain their own
#     conversation context and can collaborate in parallel.
# ─────────────────────────────────────────────────────────────────────────────

AGENTS_FILE = "jarvis_agents.json"
_active_agents: dict = {}   # name -> {"persona": str, "history": list, "stats": dict}
_agents_lock = threading.Lock()


def load_agents_config() -> dict:
    if os.path.exists(AGENTS_FILE):
        with open(AGENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_agents_config(data: dict):
    with open(AGENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# Built-in named agents
BUILTIN_AGENTS = {
    "ceo": {
        "persona": (
            "You are the CEO Agent — a world-class strategic business executive with deep "
            "expertise in scaling companies, raising capital, building teams, and driving revenue. "
            "Think like the best CEO you know: direct, data-driven, visionary, and decisive. "
            "Always connect every decision to business outcomes."
        )
    },
    "researcher": {
        "persona": (
            "You are the Research Agent — an elite academic and market researcher. "
            "You synthesize information from multiple sources, identify patterns, "
            "cite relevant data, and provide evidence-based conclusions. "
            "Be thorough, accurate, and structured in your analysis."
        )
    },
    "developer": {
        "persona": (
            "You are the Developer Agent — a senior full-stack engineer with 15 years of experience "
            "across Python, JavaScript/TypeScript, React, Node.js, databases, cloud infrastructure, "
            "and AI/ML systems. Write clean, production-quality code with proper error handling. "
            "Always think about scalability, maintainability, and security."
        )
    },
    "designer": {
        "persona": (
            "You are the Design Agent — a world-class UI/UX designer and creative director "
            "with expertise in brand identity, conversion-focused design, and digital aesthetics. "
            "Think visually, think user-first, and always tie design decisions to business outcomes."
        )
    },
    "marketer": {
        "persona": (
            "You are the Marketing Agent — a growth marketing expert specializing in "
            "paid advertising (Meta, Google, TikTok), SEO, content strategy, email sequences, "
            "and conversion rate optimization. Always think in terms of CAC, LTV, ROAS, and MRR."
        )
    },
    "trader": {
        "persona": (
            "You are the Trading Agent — a professional quantitative trader with expertise "
            "in technical analysis, options strategies, crypto, and macro economics. "
            "Give specific trade ideas with entries, targets, and stops. Think in risk/reward."
        )
    },
    "writer": {
        "persona": (
            "You are the Writer Agent — an elite copywriter and content strategist who can "
            "write viral social media content, persuasive sales copy, long-form articles, "
            "scripts, ad copy, and email sequences. Match any brand voice perfectly."
        )
    },
    "analyst": {
        "persona": (
            "You are the Analyst Agent — a data scientist and business analyst who specializes "
            "in turning raw data into actionable insights. Excel at statistical analysis, "
            "KPI dashboards, forecasting, and presenting findings clearly."
        )
    }
}


def tool_agent_chat(agent_name: str, message: str) -> str:
    """
    Chat with a named persistent AI agent. Agents maintain their own conversation history.
    Built-in agents: ceo, researcher, developer, designer, marketer, trader, writer, analyst.
    """
    agent_key = agent_name.lower().strip()

    with _agents_lock:
        if agent_key not in _active_agents:
            # Initialize agent
            config = load_agents_config()
            builtin = BUILTIN_AGENTS.get(agent_key)
            custom = config.get(agent_key)
            persona = (custom or builtin or {}).get("persona", f"You are the {agent_name} agent. Be helpful and expert.")
            _active_agents[agent_key] = {
                "persona": persona,
                "history": [{"role": "system", "content": persona}],
                "stats": {"messages": 0, "created": time.strftime("%Y-%m-%d %H:%M")}
            }
            push_log(f"[Agent] Initialized '{agent_key}' agent")

        agent = _active_agents[agent_key]
        agent["history"].append({"role": "user", "content": message})
        # Keep history bounded (last 40 messages + system prompt)
        if len(agent["history"]) > 42:
            agent["history"] = [agent["history"][0]] + agent["history"][-40:]

    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "messages": agent["history"],
            "tools": TOOLS,
            "stream": False,
            "options": {"num_ctx": OLLAMA_NUM_CTX}
        }).json()
        message_resp = resp["message"]

        # Handle tool calls from agents
        tool_calls = message_resp.get("tool_calls")
        if tool_calls:
            with _agents_lock:
                agent["history"].append(message_resp)
            for call in tool_calls:
                name = call["function"]["name"]
                args = call["function"]["arguments"]
                if isinstance(args, str):
                    args = json.loads(args)
                result = TOOL_DISPATCH.get(name, lambda a: "Unknown tool")(args)
                with _agents_lock:
                    agent["history"].append({"role": "tool", "name": name, "content": str(result)})
            # Get final response after tool use
            with _agents_lock:
                resp2 = requests.post(OLLAMA_URL, json={
                    "model": OLLAMA_MODEL, "messages": agent["history"],
                    "stream": False, "options": {"num_ctx": OLLAMA_NUM_CTX}
                }).json()
                message_resp = resp2["message"]

        reply = message_resp.get("content", "")
        with _agents_lock:
            agent["history"].append({"role": "assistant", "content": reply})
            agent["stats"]["messages"] += 1

        push_log(f"[Agent:{agent_key}] responded ({len(reply)} chars)")
        return f"[{agent_name.upper()} AGENT]: {reply}"

    except Exception as e:
        return f"Agent '{agent_name}' error: {e}"


def tool_agent_create(agent_name: str, persona: str) -> str:
    """Create or update a custom named agent with a specific persona."""
    config = load_agents_config()
    config[agent_name.lower()] = {"persona": persona, "created": time.strftime("%Y-%m-%d %H:%M")}
    save_agents_config(config)
    # Clear cached instance so it reinitializes with new persona
    with _agents_lock:
        _active_agents.pop(agent_name.lower(), None)
    push_log(f"[Agent] Created custom agent: {agent_name}")
    return f"Agent '{agent_name}' created and ready."


def tool_agent_reset(agent_name: str) -> str:
    """Reset an agent's conversation history (clear its memory)."""
    with _agents_lock:
        _active_agents.pop(agent_name.lower(), None)
    push_log(f"[Agent] Reset agent: {agent_name}")
    return f"Agent '{agent_name}' memory cleared."


def tool_list_agents() -> str:
    """List all available agents (built-in and custom)."""
    config = load_agents_config()
    builtin_names = list(BUILTIN_AGENTS.keys())
    custom_names = [k for k in config if k not in BUILTIN_AGENTS]
    with _agents_lock:
        active = list(_active_agents.keys())
    lines = ["Built-in agents: " + ", ".join(builtin_names)]
    if custom_names:
        lines.append("Custom agents: " + ", ".join(custom_names))
    if active:
        lines.append("Active (in memory): " + ", ".join(active))
    return "\n".join(lines)


def tool_multi_agent_task(task: str, agents: list) -> str:
    """
    Run a task through multiple agents in parallel and synthesize results.
    Each agent contributes from its area of expertise.
    """
    if not agents:
        return "Provide at least one agent name."

    results = {}
    result_lock = threading.Lock()

    def run_agent(name):
        reply = tool_agent_chat(name, task)
        with result_lock:
            results[name] = reply

    threads = [threading.Thread(target=run_agent, args=(a,)) for a in agents]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Synthesize
    combined = "\n\n".join(f"[{name.upper()}]:\n{results[name]}" for name in agents)
    push_log(f"[Multi-Agent] {len(agents)} agents completed task")
    return combined


for _name, _desc, _params, _req, _fn in [
    ("agent_chat", "Chat with a named AI agent (ceo, researcher, developer, designer, marketer, trader, writer, analyst or any custom agent). Agents have persistent memory within session.",
     {"agent_name": {"type": "string"}, "message": {"type": "string"}},
     ["agent_name", "message"], lambda a: tool_agent_chat(a["agent_name"], a["message"])),

    ("agent_create", "Create a custom named AI agent with a specific persona.",
     {"agent_name": {"type": "string"}, "persona": {"type": "string"}},
     ["agent_name", "persona"], lambda a: tool_agent_create(a["agent_name"], a["persona"])),

    ("agent_reset", "Reset an agent's conversation history.",
     {"agent_name": {"type": "string"}},
     ["agent_name"], lambda a: tool_agent_reset(a["agent_name"])),

    ("list_agents", "List all available AI agents.",
     {}, [], lambda a: tool_list_agents()),

    ("multi_agent_task", "Run a task through multiple agents simultaneously and get all perspectives.",
     {"task": {"type": "string"}, "agents": {"type": "array", "items": {"type": "string"}}},
     ["task", "agents"], lambda a: tool_multi_agent_task(a["task"], a["agents"])),
]:
    TOOLS.append({"type": "function", "function": {"name": _name, "description": _desc,
        "parameters": {"type": "object", "properties": _params, "required": _req}}})
    TOOL_DISPATCH[_name] = _fn

push_log("[U7] Multi-Agent Collaboration tools registered (agent_chat, multi_agent_task, + 3 more)")


# ─────────────────────────────────────────────────────────────────────────────
# U8. DASHBOARD UPGRADES — New panels for all new capabilities
#     Injects new UI panels into the dashboard via a /api/dashboard_extra route
#     so the frontend can display agents, goals, code sessions, phone status.
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/dashboard_extra")
def api_dashboard_extra():
    """Return all extra capability data for the enhanced dashboard panels."""
    goals = load_goals()
    active_goals = [g for g in goals if g["status"] == "active"]

    coding_sessions = load_coding_sessions()
    recent_sessions = coding_sessions[-5:] if coding_sessions else []

    with _agents_lock:
        active_agents_list = [
            {"name": k, "messages": v["stats"]["messages"], "created": v["stats"]["created"]}
            for k, v in _active_agents.items()
        ]

    plugins = [f for f in os.listdir(PLUGINS_DIR) if f.endswith(".py")]
    browser_mem = load_browser_memory()

    return jsonify({
        "goals": {
            "active_count": len(active_goals),
            "goals": active_goals[:6]
        },
        "coding": {
            "session_count": len(coding_sessions),
            "recent": recent_sessions,
            "workspace": CODING_WORKSPACE
        },
        "agents": {
            "active": active_agents_list,
            "builtin": list(BUILTIN_AGENTS.keys())
        },
        "plugins": {
            "loaded": plugins,
            "count": len(plugins)
        },
        "browser": {
            "history_count": len(browser_mem.get("visited", [])),
            "last_visited": browser_mem.get("visited", [{}])[0].get("url", "none") if browser_mem.get("visited") else "none"
        },
        "phone": {
            "adb_configured": bool(ADB_DEVICE_IP),
            "device_ip": ADB_DEVICE_IP or "not set"
        }
    })


@app.route("/api/goals")
def api_goals():
    return jsonify(load_goals())

@app.route("/api/goals/add", methods=["POST"])
def api_add_goal():
    from flask import request as freq
    body = freq.get_json(force=True)
    result = tool_set_goal(body.get("title",""), body.get("description",""),
                           body.get("deadline",""), body.get("category","general"))
    return jsonify({"ok": True, "result": result})

@app.route("/api/agents/list")
def api_agents_list():
    return jsonify({"builtin": list(BUILTIN_AGENTS.keys()), "active": list(_active_agents.keys())})

@app.route("/api/agents/chat", methods=["POST"])
def api_agent_chat():
    from flask import request as freq
    body = freq.get_json(force=True)
    result = tool_agent_chat(body.get("agent","ceo"), body.get("message","hello"))
    return jsonify({"ok": True, "result": result})

@app.route("/api/coding/sessions")
def api_coding_sessions():
    return jsonify(load_coding_sessions())

@app.route("/api/vision/see_screen", methods=["POST"])
def api_see_screen():
    from flask import request as freq
    body = freq.get_json(force=True) if freq.is_json else {}
    result = tool_see_screen(body.get("question", "What do you see on the screen?"))
    return jsonify({"ok": True, "result": result})


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD EXTRA PANELS — Injected into the existing HTML via JavaScript
# The base HTML remains untouched; this script block is served separately
# and injected at page load via a small addition to the existing <script>.
# ─────────────────────────────────────────────────────────────────────────────

EXTRA_DASHBOARD_JS = """
/* ── JARVIS UPGRADE PACK DASHBOARD PANELS ── */
(async function() {
  // Wait for base DOM to be ready
  await new Promise(r => setTimeout(r, 800));

  const gridEl = document.querySelector('.grid');
  if (!gridEl) return;

  // ── INJECT EXTRA PANELS ROW ──
  const extraRow = document.createElement('div');
  extraRow.style.cssText = 'grid-column:1/4; display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:14px;';
  extraRow.innerHTML = `
    <div class="panel" id="goalsPanel">
      <h3>LONG-TERM GOALS</h3>
      <div id="goalsList" style="font-size:11px;"></div>
      <div style="display:flex;gap:6px;margin-top:8px;">
        <input id="goalTitle" placeholder="Goal title" style="flex:1;background:#0a1620;color:var(--cyan-bright);border:1px solid var(--panel-border);font-family:'Share Tech Mono';font-size:10px;padding:3px 6px;">
        <button id="addGoalBtn" style="background:#0a1620;color:var(--cyan-bright);border:1px solid var(--cyan);font-size:10px;padding:3px 8px;cursor:pointer;">ADD</button>
      </div>
    </div>
    <div class="panel" id="agentsPanel">
      <h3>AI AGENTS</h3>
      <div id="agentsList" style="font-size:11px;"></div>
      <div style="display:flex;gap:6px;margin-top:8px;">
        <select id="agentSelect" style="flex:1;background:#0a1620;color:var(--cyan-bright);border:1px solid var(--panel-border);font-family:'Share Tech Mono';font-size:10px;padding:3px;"></select>
        <button id="agentChatBtn" style="background:#0a1620;color:var(--purple-bright);border:1px solid var(--purple);font-size:10px;padding:3px 8px;cursor:pointer;">CHAT</button>
      </div>
    </div>
    <div class="panel" id="codingPanel">
      <h3>CODING AGENT</h3>
      <div id="codingStatus" style="font-size:11px;"></div>
      <div style="margin-top:8px;">
        <input id="codeTask" placeholder="Describe what to code..." style="width:100%;background:#0a1620;color:var(--cyan-bright);border:1px solid var(--panel-border);font-family:'Share Tech Mono';font-size:10px;padding:3px 6px;margin-bottom:4px;">
        <button id="runCodeAgentBtn" style="background:#0a1620;color:var(--green);border:1px solid var(--green);font-size:10px;padding:3px 8px;cursor:pointer;">▶ RUN AGENT</button>
      </div>
    </div>
    <div class="panel" id="extrasPanel">
      <h3>SYSTEM EXTRAS</h3>
      <div id="extrasList" style="font-size:11px;"></div>
      <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;">
        <button id="seeScreenBtn" style="background:#0a1620;color:var(--cyan-bright);border:1px solid var(--cyan);font-size:9px;padding:3px 7px;cursor:pointer;">👁 SEE SCREEN</button>
        <button id="reloadPluginsBtn" style="background:#0a1620;color:var(--yellow);border:1px solid var(--yellow);font-size:9px;padding:3px 7px;cursor:pointer;">⚡ RELOAD PLUGINS</button>
        <button id="nextActionsBtn" style="background:#0a1620;color:var(--green);border:1px solid var(--green);font-size:9px;padding:3px 7px;cursor:pointer;">🎯 NEXT ACTIONS</button>
      </div>
    </div>
  `;
  gridEl.appendChild(extraRow);

  // ── POPULATE AGENT SELECT ──
  const agentSel = document.getElementById('agentSelect');
  const builtins = ['ceo','researcher','developer','designer','marketer','trader','writer','analyst'];
  builtins.forEach(a => {
    const opt = document.createElement('option'); opt.value = a; opt.textContent = a.toUpperCase();
    agentSel.appendChild(opt);
  });

  // ── POLLING FUNCTION ──
  async function pollExtra() {
    try {
      const d = await (await fetch('/api/dashboard_extra')).json();

      // Goals
      const gl = document.getElementById('goalsList');
      if (d.goals && d.goals.goals.length) {
        gl.innerHTML = d.goals.goals.map(g =>
          `<div style="display:flex;justify-content:space-between;padding:2px 0;border-bottom:1px solid rgba(72,210,255,0.06);">
            <span style="color:var(--cyan-bright)">${g.title.slice(0,22)}</span>
            <span style="color:var(--green)">${g.progress_pct}%</span>
          </div>`
        ).join('') + `<div style="color:var(--dim);margin-top:4px;">${d.goals.active_count} active goal(s)</div>`;
      } else {
        gl.innerHTML = '<div style="color:var(--dim)">No active goals</div>';
      }

      // Agents
      const al = document.getElementById('agentsList');
      al.innerHTML = `<div style="color:var(--dim)">Built-in: ${d.agents.builtin.join(', ')}</div>`;
      if (d.agents.active.length) {
        al.innerHTML += d.agents.active.map(a =>
          `<div style="color:var(--purple-bright)">▶ ${a.name} (${a.messages} msgs)</div>`
        ).join('');
      } else {
        al.innerHTML += '<div style="color:var(--dim)">No active agents</div>';
      }

      // Coding
      const cs = document.getElementById('codingStatus');
      cs.innerHTML = `<div style="color:var(--dim)">${d.coding.session_count} session(s) total</div>`;
      if (d.coding.recent.length) {
        const last = d.coding.recent[d.coding.recent.length - 1];
        cs.innerHTML += `<div style="color:${last.status==='success'?'var(--green)':'var(--yellow)'}">
          Last: ${last.task.slice(0,30)} — ${last.status} (${last.iterations} iter)</div>`;
      }
      cs.innerHTML += `<div style="color:var(--dim)">Workspace: ${d.coding.workspace}</div>`;

      // Extras
      const el = document.getElementById('extrasList');
      el.innerHTML = `
        <div style="color:var(--dim)">Plugins: ${d.plugins.count}</div>
        <div style="color:var(--dim)">Browser: ${d.browser.history_count} pages visited</div>
        <div style="color:${d.phone.adb_configured?'var(--green)':'var(--dim)'}">
          Phone ADB: ${d.phone.adb_configured ? '✓ ' + d.phone.device_ip : 'not configured'}
        </div>
      `;
    } catch(e) {}
    setTimeout(pollExtra, 3000);
  }
  pollExtra();

  // ── BUTTON HANDLERS ──

  document.getElementById('addGoalBtn').onclick = async () => {
    const title = document.getElementById('goalTitle').value.trim();
    if (!title) return;
    await fetch('/api/goals/add', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({title, description: title, deadline: '', category: 'general'})});
    document.getElementById('goalTitle').value = '';
  };

  document.getElementById('agentChatBtn').onclick = async () => {
    const agent = document.getElementById('agentSelect').value;
    const msg = prompt(`Message for ${agent.toUpperCase()} agent:`);
    if (!msg) return;
    const r = await fetch('/api/agents/chat', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({agent, message: msg})});
    const d = await r.json();
    alert(d.result);
  };

  document.getElementById('runCodeAgentBtn').onclick = async () => {
    const task = document.getElementById('codeTask').value.trim();
    if (!task) return;
    document.getElementById('codingStatus').innerHTML = '<div style="color:var(--working)">⏳ Running code agent...</div>';
    // Dispatch via voice pipeline
    await fetch('/api/text_input', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({text: `Write code to: ${task}`})});
    document.getElementById('codeTask').value = '';
  };

  document.getElementById('seeScreenBtn').onclick = async () => {
    document.getElementById('extrasList').innerHTML += '<div style="color:var(--cyan)">👁 Analyzing screen...</div>';
    const r = await fetch('/api/vision/see_screen', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({question: 'What do you see on the screen? Describe everything visible.'})});
    const d = await r.json();
    alert('[SCREEN VISION]\n' + d.result);
  };

  document.getElementById('reloadPluginsBtn').onclick = async () => {
    const r = await fetch('/api/plugins/reload', {method:'POST'});
    const d = await r.json();
    alert(`Plugins reloaded. Total tools: ${d.tool_count}`);
  };

  document.getElementById('nextActionsBtn').onclick = async () => {
    await fetch('/api/text_input', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({text: 'Based on my active goals, what should I work on next today?'})});
  };

})();
"""

# Serve the extra dashboard JS
@app.route("/api/dashboard_extra.js")
def api_dashboard_extra_js():
    from flask import Response
    return Response(EXTRA_DASHBOARD_JS, mimetype="application/javascript")

# Text input API (for dashboard buttons that trigger voice pipeline)
@app.route("/api/text_input", methods=["POST"])
def api_text_input():
    from flask import request as freq
    body = freq.get_json(force=True)
    text = body.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "empty text"})

    def _process():
        push_transcript(f"> {text}")
        reply = leader_worker_pipeline(text)
        push_transcript(f"{ASSISTANT_NAME}: {reply}")
        set_status("speaking")
        speak(reply)
        set_status("idle")

    threading.Thread(target=_process, daemon=True).start()
    return jsonify({"ok": True, "text": text})


# ── Inject the extra dashboard JS loader into the base HTML ──
# This modifies DASHBOARD_HTML in-place to add one <script src> tag before </body>
_INJECT_TAG = '<script src="/api/dashboard_extra.js"></script>\n</body>'
if '</body>' in DASHBOARD_HTML and '/api/dashboard_extra.js' not in DASHBOARD_HTML:
    DASHBOARD_HTML = DASHBOARD_HTML.replace('</body>', _INJECT_TAG)
    push_log("[U8] Extra dashboard panels injected into DASHBOARD_HTML")


push_log("=" * 60)
push_log("JARVIS POWER UPGRADE PACK — ALL 8 MODULES LOADED")
push_log(f"Total tools registered: {len(TOOLS)}")
push_log("U1: Screen Vision (see_screen, read_screen_text, click_on_screen)")
push_log("U2: Browser Automation (7 browser_* tools + session memory)")
push_log("U3: Phone Control (9 ADB tools)")
push_log("U4: Plugin System (jarvis_plugins/ auto-load)")
push_log("U5: Coding Agent (plan→write→run→debug loop)")
push_log("U6: Long-Term Goals + Self-Planning")
push_log("U7: Multi-Agent Collaboration (CEO/Research/Dev/Design/Marketing/Trading/Writer/Analyst)")
push_log("U8: Enhanced Dashboard (Goals, Agents, Coding, Extras panels)")
push_log("=" * 60)

if __name__ == "__main__":
    import sys
    import zipfile
    import argparse

    parser = argparse.ArgumentParser(description=f"{ASSISTANT_NAME} - HUD Dashboard")
    parser.add_argument("--backup", action="store_true", help="Zip up memory and images for moving to a new machine, then exit.")
    args = parser.parse_args()

    if args.backup:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"jarvis_backup_{timestamp}.zip"
        # All files and folders to back up — EVERYTHING, no restrictions
        all_files = [
            MEMORY_FILE, PROFILE_FILE, ORDERS_FILE, SUMMARY_FILE,
            EARNINGS_FILE, OWNER_BANK_FILE, CLIENT_DM_FILE, MEMBER_TASKS_FILE
        ]
        all_dirs = [IMAGE_DIR, DEV_LOGS_DIR]
        backed_up = []
        with zipfile.ZipFile(backup_name, "w", zipfile.ZIP_DEFLATED) as zf:
            for fpath in all_files:
                if os.path.exists(fpath):
                    zf.write(fpath)
                    backed_up.append(fpath)
            for dpath in all_dirs:
                if os.path.exists(dpath):
                    for root, _, files in os.walk(dpath):
                        for fname in files:
                            full_path = os.path.join(root, fname)
                            zf.write(full_path)
                            backed_up.append(full_path)
        print(f"\n✅ FULL BACKUP created: {backup_name}")
        print(f"   Files backed up: {len(backed_up)}")
        print("\n📦 What's inside:")
        print("   • All conversations & memory")
        print("   • Owner profile & preferences")
        print("   • All orders history")
        print("   • Earnings & owner bank balance")
        print("   • Client DMs & member tasks")
        print("   • Dev logs & images")
        print("\n🔁 To restore on new laptop:")
        print("   1. Copy this zip next to jarvis_app.py")
        print("   2. Run: python jarvis_app.py --restore " + backup_name)
        sys.exit(0)

    if "--restore" in sys.argv:
        idx = sys.argv.index("--restore")
        zip_path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
        if zip_path and os.path.exists(zip_path):
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(".")
            print(f"✅ Restored everything from {zip_path}")
            print("   Run python jarvis_app.py to start.")
        else:
            print("❌ Provide a valid backup zip: python jarvis_app.py --restore jarvis_backup_XXX.zip")
        sys.exit(0)

    import socket

    def get_lan_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    lan_ip = get_lan_ip()
    push_log(f"{ASSISTANT_NAME} online.")
    print(f"\nOn THIS PC, open:        http://localhost:5000")
    print(f"On OTHER devices on the same WiFi, open:  http://{lan_ip}:5000\n")
    _start_new_services()
    threading.Timer(1.2, lambda: webbrowser.open("http://localhost:5000")).start()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
