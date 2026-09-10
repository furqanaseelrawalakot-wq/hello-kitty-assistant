/* =========================================================
   Hello Kitty AI Assistant — Client Script
   Alexa-Style Voice Recording (SpeechRecognition),
   Spoken Voice Output (SpeechSynthesis),
   Glassmorphism Chat & Landing Screen Transitions.
   ========================================================= */

(function() {
    'use strict';

    console.log('[Hello Kitty Client] Initializing Alexa-style voice interface...');

    // DOM Elements
    const landingScreen = document.getElementById('landing-screen');
    const startChatBtn = document.getElementById('start-chat-btn');
    const backToLandingBtn = document.getElementById('back-to-landing-btn');
    const chatContainer = document.getElementById('chat-container');
    const chatMessages = document.getElementById('chat-messages');
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const clearBtn = document.getElementById('clear-btn');
    const micBtn = document.getElementById('mic-btn');
    const micLangBtn = document.getElementById('mic-lang-btn');
    const micLangLabel = document.getElementById('mic-lang-label');
    const landingVoiceBtn = document.getElementById('landing-voice-btn');
    const micStatusBanner = document.getElementById('mic-status-banner');
    const micStatusText = document.getElementById('mic-status-text');
    const voiceToggleBtn = document.getElementById('voice-toggle-btn');
    const voiceToggleIcon = document.getElementById('voice-toggle-icon');
    const voiceToggleLabel = document.getElementById('voice-toggle-label');
    const musicControllerBar = document.getElementById('music-controller-bar');
    const musicBarTitle = document.getElementById('music-bar-title');
    const musicPauseBtn = document.getElementById('music-pause-btn');
    const musicPauseIcon = document.getElementById('music-pause-icon');
    const musicPauseLabel = document.getElementById('music-pause-label');
    const musicStopBtn = document.getElementById('music-stop-btn');
    const mobileConnectBtn = document.getElementById('mobile-connect-btn');
    const mobileModal = document.getElementById('mobile-modal');
    const mobileModalBackdrop = document.getElementById('mobile-modal-backdrop');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const copyUrlBtn = document.getElementById('copy-url-btn');
    const mobileUrlInput = document.getElementById('mobile-url-input');
    const copyUrlText = document.getElementById('copy-url-text');
    const copyUrlIcon = document.getElementById('copy-url-icon');

    let isSubmitting = false;
    let isRecording = false;
    let isVoiceOutputEnabled = true;
    let currentVoiceLang = 'en-US';
    let recognition = null;
    let mediaRecorder = null;
    let audioChunks = [];
    let mediaStream = null;
    let currentMusicPlaying = false;
    let currentMusicPaused = false;
    let currentMusicTrack = '';

    // --- Music Controller Functions ---
    function updateMusicBar(info) {
        if (!musicControllerBar) return;
        if (info.is_playing || info.is_paused) {
            musicControllerBar.classList.remove('music-bar-hidden');
            if (info.title) {
                currentMusicTrack = info.title;
                if (musicBarTitle) musicBarTitle.textContent = info.title;
            }
            if (info.is_paused) {
                currentMusicPaused = true;
                currentMusicPlaying = false;
                if (musicPauseIcon) musicPauseIcon.textContent = '▶️';
                if (musicPauseLabel) musicPauseLabel.textContent = 'Resume';
                musicControllerBar.classList.add('paused');
            } else {
                currentMusicPaused = false;
                currentMusicPlaying = true;
                if (musicPauseIcon) musicPauseIcon.textContent = '⏸️';
                if (musicPauseLabel) musicPauseLabel.textContent = 'Pause';
                musicControllerBar.classList.remove('paused');
            }
        } else {
            musicControllerBar.classList.add('music-bar-hidden');
            currentMusicPlaying = false;
            currentMusicPaused = false;
        }
    }

    async function toggleMusicPause() {
        if (currentMusicPaused) {
            try {
                const res = await fetch('/music/resume', { method: 'POST' });
                const d = await res.json();
                updateMusicBar({ is_playing: true, is_paused: false, title: currentMusicTrack });
                document.querySelectorAll('audio.kitty-audio-player').forEach(a => {
                    try { a.play(); } catch (e) {}
                });
                if (d.reply) appendMessage('ai', d.reply);
            } catch (err) {
                console.warn('Music resume error:', err);
            }
        } else {
            try {
                const res = await fetch('/music/pause', { method: 'POST' });
                const d = await res.json();
                updateMusicBar({ is_playing: false, is_paused: true, title: currentMusicTrack });
                document.querySelectorAll('audio.kitty-audio-player').forEach(a => {
                    try { a.pause(); } catch (e) {}
                });
                if (d.reply) appendMessage('ai', d.reply);
            } catch (err) {
                console.warn('Music pause error:', err);
            }
        }
    }

    async function stopMusicAction() {
        try {
            const res = await fetch('/music/stop', { method: 'POST' });
            const d = await res.json();
            updateMusicBar({ is_playing: false, is_paused: false });
            document.querySelectorAll('audio.kitty-audio-player').forEach(a => {
                try { a.pause(); a.currentTime = 0; } catch (e) {}
            });
            if (d.reply) appendMessage('ai', d.reply);
        } catch (err) {
            console.warn('Music stop error:', err);
        }
    }

    window.toggleKittyMusic = toggleMusicPause;
    window.stopKittyMusic = stopMusicAction;

    if (musicPauseBtn) {
        musicPauseBtn.addEventListener('click', toggleMusicPause);
    }
    if (musicStopBtn) {
        musicStopBtn.addEventListener('click', stopMusicAction);
    }

    // --- Screen Transition Handlers ---
    function openChatView() {
        console.log('[Hello Kitty Client] Transitioning to Chat view...');
        if (landingScreen) {
            landingScreen.classList.add('landing-hidden');
        }
        if (chatContainer) {
            chatContainer.classList.remove('chat-hidden');
            chatContainer.classList.add('chat-active');
        }
        setTimeout(() => {
            if (userInput) {
                userInput.focus();
            }
        }, 400);
    }

    function openLandingView() {
        console.log('[Hello Kitty Client] Returning to Landing view...');
        if (chatContainer) {
            chatContainer.classList.remove('chat-active');
            chatContainer.classList.add('chat-hidden');
        }
        if (landingScreen) {
            landingScreen.classList.remove('landing-hidden');
        }
        // Stop any active speech or recording
        stopRecording();
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
    }

    if (startChatBtn) {
        startChatBtn.addEventListener('click', openChatView);
    }

    if (landingVoiceBtn) {
        landingVoiceBtn.addEventListener('click', function() {
            openChatView();
            if (micStatusBanner && micStatusText) {
                micStatusBanner.classList.remove('mic-banner-hidden');
                micStatusText.textContent = 'Tap the microphone 🎙️ below to start speaking!';
                setTimeout(() => {
                    if (micStatusBanner && !isRecording) {
                        micStatusBanner.classList.add('mic-banner-hidden');
                    }
                }, 4000);
            }
        });
    }

    if (backToLandingBtn) {
        backToLandingBtn.addEventListener('click', openLandingView);
    }

    // --- Voice Output (Text-To-Speech) ---
    function speakAloud(text) {
        if (!isVoiceOutputEnabled || !('speechSynthesis' in window) || !text) {
            return;
        }

        try {
            window.speechSynthesis.cancel(); // Stop any pending speech

            // Clean text (remove URLs and emojis for cleaner speech)
            const cleanText = text
                .replace(/https?:\/\/\S+/g, '')
                .replace(/[🎀⏰📅🌤️🔔🎵🎤🇵🇰🐱⚠️]/g, '')
                .trim();

            if (!cleanText) return;

            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.rate = 1.0;
            utterance.pitch = 1.15; // Slightly higher, cheerful pitch for Hello Kitty

            // Try to pick a pleasant voice
            const voices = window.speechSynthesis.getVoices();
            const preferredVoice = voices.find(v => 
                v.lang.startsWith('en') && (v.name.includes('Female') || v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Zira'))
            ) || voices.find(v => v.lang.startsWith('en'));

            if (preferredVoice) {
                utterance.voice = preferredVoice;
            }

            window.speechSynthesis.speak(utterance);
        } catch (err) {
            console.warn('[Hello Kitty Client] SpeechSynthesis error:', err);
        }
    }

    // Voice Output Toggle
    if (voiceToggleBtn) {
        voiceToggleBtn.addEventListener('click', function() {
            isVoiceOutputEnabled = !isVoiceOutputEnabled;
            if (isVoiceOutputEnabled) {
                voiceToggleBtn.classList.add('active');
                if (voiceToggleIcon) voiceToggleIcon.textContent = '🔊';
                if (voiceToggleLabel) voiceToggleLabel.textContent = 'Voice: ON';
                speakAloud("Voice is now turned on!");
            } else {
                voiceToggleBtn.classList.remove('active');
                if (voiceToggleIcon) voiceToggleIcon.textContent = '🔇';
                if (voiceToggleLabel) voiceToggleLabel.textContent = 'Voice: OFF';
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                }
            }
        });
    }

    // Language Toggle: English (en-US) vs Urdu (ur-PK)
    if (micLangBtn) {
        micLangBtn.addEventListener('click', function() {
            if (currentVoiceLang === 'en-US') {
                currentVoiceLang = 'ur-PK';
                if (micLangLabel) micLangLabel.textContent = '🇵🇰 UR';
                micLangBtn.title = 'Language: Urdu (click to switch to English)';
            } else {
                currentVoiceLang = 'en-US';
                if (micLangLabel) micLangLabel.textContent = '🇺🇸 EN';
                micLangBtn.title = 'Language: English (click to switch to Urdu)';
            }
            console.log('[Hello Kitty Client] Voice language switched to:', currentVoiceLang);
        });
    }

    // --- Dual-Engine Voice Recording (SpeechRecognition + MediaRecorder / WebAudio Fallback) ---
    let audioContext = null;
    let audioProcessor = null;
    let pcmSamples = [];
    let recordStartTime = 0;

    function encodeWavBlob(samples, sampleRate) {
        let totalSamples = 0;
        for (let i = 0; i < samples.length; i++) {
            totalSamples += samples[i].length;
        }
        const flat = new Float32Array(totalSamples);
        let offset = 0;
        for (let i = 0; i < samples.length; i++) {
            flat.set(samples[i], offset);
            offset += samples[i].length;
        }

        const buffer = new ArrayBuffer(44 + flat.length * 2);
        const view = new DataView(buffer);

        function writeStr(view, off, str) {
            for (let i = 0; i < str.length; i++) {
                view.setUint8(off + i, str.charCodeAt(i));
            }
        }

        writeStr(view, 0, 'RIFF');
        view.setUint32(4, 36 + flat.length * 2, true);
        writeStr(view, 8, 'WAVE');
        writeStr(view, 12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true); // PCM format
        view.setUint16(22, 1, true); // Mono 1 channel
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * 2, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeStr(view, 36, 'data');
        view.setUint32(40, flat.length * 2, true);

        let dataOffset = 44;
        for (let i = 0; i < flat.length; i++, dataOffset += 2) {
            let s = Math.max(-1, Math.min(1, flat[i]));
            view.setInt16(dataOffset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }
        return new Blob([buffer], { type: 'audio/wav' });
    }

    function stopRecording() {
        isRecording = false;
        if (micBtn) {
            micBtn.classList.remove('recording');
            micBtn.title = 'Click to speak (Alexa/Siri voice recording)';
        }
        if (micStatusBanner) {
            micStatusBanner.classList.add('mic-banner-hidden');
        }
        if (audioProcessor) {
            try { audioProcessor.disconnect(); } catch (e) {}
            audioProcessor = null;
        }
        if (audioContext && audioContext.state !== 'closed') {
            try { audioContext.close(); } catch (e) {}
            audioContext = null;
        }
        if (recognition) {
            try { 
                recognition.abort(); 
            } catch (e) {}
            recognition = null;
        }
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            try { 
                mediaRecorder.stop(); 
            } catch (e) {}
        }
        if (mediaStream) {
            try {
                mediaStream.getTracks().forEach(track => track.stop());
            } catch (e) {}
            mediaStream = null;
        }
    }

    // Engine 1: Client-Side Web Speech API with Siri-Style Real-Time Interim Typing
    function startSpeechRecognitionEngine() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.log('[Hello Kitty Client] SpeechRecognition API not supported. Using MediaRecorder fallback.');
            startMediaRecorderEngine();
            return;
        }

        try {
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true; // Live typing as you speak!
            recognition.lang = currentVoiceLang;

            let finalTranscript = '';
            let hasFinalSent = false;

            recognition.onstart = function() {
                isRecording = true;
                if (micBtn) micBtn.classList.add('recording');
                if (micStatusBanner) micStatusBanner.classList.remove('mic-banner-hidden');
                if (micStatusText) {
                    micStatusText.textContent = `Listening (${currentVoiceLang === 'ur-PK' ? 'اردو' : 'English'})... Speak now!`;
                }
                console.log('[Hello Kitty Client] SpeechRecognition active with real-time feedback.');
            };

            recognition.onresult = function(event) {
                let interim = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    } else {
                        interim += event.results[i][0].transcript;
                    }
                }

                const liveText = (finalTranscript || interim).trim();
                if (liveText) {
                    // Live typing effect like Siri!
                    if (userInput) userInput.value = liveText;
                    if (micStatusText) micStatusText.textContent = `Hearing: "${liveText}"`;
                }

                // Check if final speech result has completed
                if (event.results[0] && event.results[0].isFinal && !hasFinalSent) {
                    const cleanTranscript = (finalTranscript || liveText).trim();
                    console.log('[Hello Kitty Client] Final speech result:', cleanTranscript);
                    hasFinalSent = true;
                    stopRecording();
                    if (cleanTranscript) {
                        handleSendMessage(cleanTranscript);
                    }
                }
            };

            recognition.onerror = function(event) {
                console.warn('[Hello Kitty Client] SpeechRecognition error:', event.error);
                if (event.error === 'service-not-allowed' || event.error === 'network') {
                    console.log('[Hello Kitty Client] Falling back to MediaRecorder on error:', event.error);
                    stopRecording();
                    startMediaRecorderEngine();
                    return;
                }

                let userFriendlyError = '';
                if (event.error === 'not-allowed') {
                    userFriendlyError = 'Microphone access was denied. Please allow mic access in your address bar.';
                    appendMessage('ai', '🔒 ' + userFriendlyError);
                } else if (event.error === 'no-speech') {
                    userFriendlyError = "Didn't catch that — please click the mic and speak clearly.";
                } else if (event.error === 'audio-capture') {
                    userFriendlyError = 'No microphone was detected on your device.';
                    appendMessage('ai', '🎙️ ' + userFriendlyError);
                } else if (event.error === 'aborted') {
                    stopRecording();
                    return;
                } else {
                    userFriendlyError = `Microphone notice: ${event.error}`;
                }

                if (micStatusText) micStatusText.textContent = userFriendlyError;
                setTimeout(stopRecording, 2500);
            };

            recognition.onend = function() {
                if (isRecording && !hasFinalSent) {
                    const transcript = userInput ? userInput.value.trim() : '';
                    stopRecording();
                    if (transcript) {
                        hasFinalSent = true;
                        handleSendMessage(transcript);
                    }
                } else {
                    stopRecording();
                }
            };

            recognition.start();

        } catch (err) {
            console.warn('[Hello Kitty Client] SpeechRecognition start failed, trying MediaRecorder:', err);
            startMediaRecorderEngine();
        }
    }

    // Engine 2: Direct 16kHz PCM WAV AudioContext + MediaRecorder Fallback + Silence Gate
    async function startMediaRecorderEngine() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            const noMediaMsg = 'Your browser does not allow microphone recording. Please use Chrome, Edge, or Firefox.';
            appendMessage('ai', '⚠️ ' + noMediaMsg);
            return;
        }

        try {
            console.log('[Hello Kitty Client] Requesting microphone stream via getUserMedia...');
            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            recordStartTime = Date.now();
            pcmSamples = [];
            audioChunks = [];

            // Setup Web Audio API PCM capture (16kHz Mono)
            try {
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (AudioCtx) {
                    audioContext = new AudioCtx({ sampleRate: 16000 });
                    const srcNode = audioContext.createMediaStreamSource(mediaStream);
                    audioProcessor = audioContext.createScriptProcessor(4096, 1, 1);
                    audioProcessor.onaudioprocess = function(e) {
                        if (!isRecording) return;
                        const chData = e.inputBuffer.getChannelData(0);
                        pcmSamples.push(new Float32Array(chData));
                    };
                    srcNode.connect(audioProcessor);
                    audioProcessor.connect(audioContext.destination);
                }
            } catch (acErr) {
                console.warn('[Hello Kitty Client] AudioContext initialization failed, using standard MediaRecorder:', acErr);
            }

            const mime = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
            mediaRecorder = mime ? new MediaRecorder(mediaStream, { mimeType: mime }) : new MediaRecorder(mediaStream);

            mediaRecorder.ondataavailable = function(e) {
                if (e.data && e.data.size > 0) {
                    audioChunks.push(e.data);
                }
            };

            mediaRecorder.onstop = async function() {
                console.log('[Hello Kitty Client] Audio recording stopped. Processing...');
                if (micStatusText) micStatusText.textContent = 'Processing your speech...';
                if (micBtn) micBtn.classList.remove('recording');

                const durationMs = Date.now() - recordStartTime;
                if (durationMs < 800) {
                    console.log('[Hello Kitty Client] Recording too short (', durationMs, 'ms), ignoring quick tap.');
                    stopRecording();
                    return;
                }

                // Check for silence using RMS
                let sumSquares = 0;
                let sampleCount = 0;
                for (let i = 0; i < pcmSamples.length; i++) {
                    const chunk = pcmSamples[i];
                    for (let j = 0; j < chunk.length; j += 8) {
                        sumSquares += chunk[j] * chunk[j];
                        sampleCount++;
                    }
                }
                const rms = sampleCount > 0 ? Math.sqrt(sumSquares / sampleCount) : 0;
                console.log('[Hello Kitty Client] Recording duration:', durationMs, 'ms, RMS volume:', rms);

                if (pcmSamples.length > 0 && rms < 0.003) {
                    console.log('[Hello Kitty Client] Silence detected, skipping upload.');
                    stopRecording();
                    if (micStatusText) micStatusText.textContent = "Didn't hear you speak. Tap the mic and try again!";
                    if (micStatusBanner) micStatusBanner.classList.remove('mic-banner-hidden');
                    setTimeout(() => { if (micStatusBanner && !isRecording) micStatusBanner.classList.add('mic-banner-hidden'); }, 3000);
                    return;
                }

                let audioBlob;
                let filename = 'voice_input.webm';

                if (pcmSamples.length > 0) {
                    audioBlob = encodeWavBlob(pcmSamples, 16000);
                    filename = 'voice_input.wav';
                    console.log('[Hello Kitty Client] Generated WAV blob size:', audioBlob.size, 'bytes');
                } else if (audioChunks.length > 0) {
                    audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
                    filename = 'voice_input.webm';
                } else {
                    stopRecording();
                    return;
                }

                const formData = new FormData();
                formData.append('audio', audioBlob, filename);
                formData.append('lang', currentVoiceLang);

                showTypingIndicator();
                if (sendBtn) sendBtn.disabled = true;

                try {
                    const resp = await fetch('/voice', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await resp.json();
                    removeTypingIndicator();

                    if (data.transcript) {
                        appendMessage('user', data.transcript);
                    }
                    if (data.reply) {
                        appendMessage('ai', data.reply, data);
                        speakAloud(data.reply);
                    }
                } catch (sendErr) {
                    removeTypingIndicator();
                    console.error('[Hello Kitty Client] /voice upload error:', sendErr);
                    appendMessage('ai', '⚠️ Could not process voice recording. Please try again or type.');
                } finally {
                    stopRecording();
                    if (sendBtn) sendBtn.disabled = false;
                }
            };

            mediaRecorder.start(250);
            isRecording = true;
            if (micBtn) micBtn.classList.add('recording');
            if (micStatusBanner) micStatusBanner.classList.remove('mic-banner-hidden');
            if (micStatusText) {
                micStatusText.textContent = `Recording (${currentVoiceLang === 'ur-PK' ? 'اردو' : 'English'})... Speak now!`;
            }

        } catch (mediaErr) {
            console.error('[Hello Kitty Client] getUserMedia error:', mediaErr);
            stopRecording();
            let errText = 'Microphone permission denied. Please allow microphone access in your browser address bar.';
            if (mediaErr.name === 'NotFoundError') {
                errText = 'No microphone was found on your computer.';
            }
            appendMessage('ai', '🔒 ' + errText);
            if (micStatusBanner && micStatusText) {
                micStatusText.textContent = errText;
                micStatusBanner.classList.remove('mic-banner-hidden');
                setTimeout(() => { if (micStatusBanner) micStatusBanner.classList.add('mic-banner-hidden'); }, 3000);
            }
        }
    }

    // Main Record Button Handler
    function startRecording() {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }

        if (chatContainer && !chatContainer.classList.contains('chat-active')) {
            openChatView();
        }

        // Instant visual feedback on click
        if (micBtn) {
            micBtn.classList.add('recording');
            micBtn.title = 'Listening... Click to finish speaking';
        }
        if (micStatusBanner) {
            micStatusBanner.classList.remove('mic-banner-hidden');
        }
        if (micStatusText) {
            micStatusText.textContent = `Activating microphone (${currentVoiceLang === 'ur-PK' ? 'اردو' : 'English'})...`;
        }

        startSpeechRecognitionEngine();
    }

    if (micBtn) {
        micBtn.addEventListener('click', function() {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        });
    }

    // Format current time e.g., "11:20 AM"
    function getCurrentTimeString() {
        const now = new Date();
        return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // Auto-scroll chat window to the latest message
    function scrollToBottom() {
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    // Escape HTML to prevent injection
    function escapeHtml(string) {
        if (typeof string !== 'string') return String(string);
        const div = document.createElement('div');
        div.textContent = string;
        return div.innerHTML;
    }

    // Append a message bubble to the chat container
    function appendMessage(sender, text, meta) {
        if (!chatMessages) return;

        // Sync Music Controller Bar & Browser Audio elements based on response metadata
        if (meta) {
            if (meta.is_music && meta.music) {
                updateMusicBar({ is_playing: true, is_paused: false, title: meta.music.title });
            } else if (meta.is_music_pause) {
                updateMusicBar({ is_playing: false, is_paused: true });
                document.querySelectorAll('audio.kitty-audio-player').forEach(a => {
                    try { a.pause(); } catch (e) {}
                });
            } else if (meta.is_music_resume) {
                updateMusicBar({ is_playing: true, is_paused: false });
                document.querySelectorAll('audio.kitty-audio-player').forEach(a => {
                    try { a.play(); } catch (e) {}
                });
            } else if (meta.is_music_stop) {
                updateMusicBar({ is_playing: false, is_paused: false });
                document.querySelectorAll('audio.kitty-audio-player').forEach(a => {
                    try { a.pause(); a.currentTime = 0; } catch (e) {}
                });
            }
        }

        const rowDiv = document.createElement('div');
        rowDiv.classList.add('message-row');

        if (sender === 'user') {
            rowDiv.classList.add('user-row');
            rowDiv.innerHTML = `
                <div class="message-bubble user-bubble">${escapeHtml(text)}</div>
                <div class="message-timestamp">${getCurrentTimeString()}</div>
            `;
        } else {
            rowDiv.classList.add('ai-row');

            let weatherMapHtml = '';
            if (meta && meta.is_weather_map && meta.weather_map) {
                const w = meta.weather_map;
                const locDisplay = escapeHtml(w.display_location || w.location || 'Location');
                const condition = escapeHtml(w.condition || 'Clear');
                const emoji = escapeHtml(w.emoji || '🌤️');
                const tempC = w.temp_c !== undefined ? w.temp_c : '--';
                const tempF = w.temp_f !== undefined ? w.temp_f : '--';
                const feelsC = w.feels_like_c !== undefined ? w.feels_like_c : '--';
                const feelsF = w.feels_like_f !== undefined ? w.feels_like_f : '--';
                const maxC = w.max_temp_c !== undefined ? w.max_temp_c : '--';
                const minC = w.min_temp_c !== undefined ? w.min_temp_c : '--';
                const humidity = w.humidity !== undefined ? w.humidity : '--';
                const wind = w.wind_kmph !== undefined ? w.wind_kmph : '--';
                const rain = w.rain_chance !== undefined ? w.rain_chance : '--';
                const lat = w.latitude !== undefined ? Number(w.latitude).toFixed(3) : '0';
                const lon = w.longitude !== undefined ? Number(w.longitude).toFixed(3) : '0';
                const gMapsUrl = escapeHtml(w.google_maps_url || `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`);
                const embedUrl = escapeHtml(w.embed_map_url || '');

                weatherMapHtml = `
                    <div class="weather-map-card">
                        <div class="weather-card-header">
                            <div class="weather-loc-group">
                                <span class="weather-loc-pin">📍</span>
                                <span class="weather-loc-name">${locDisplay}</span>
                            </div>
                            <span class="weather-coords-pill">${lat}° N, ${lon}° E</span>
                        </div>

                        <div class="weather-hero-section">
                            <div class="weather-hero-main">
                                <span class="weather-hero-emoji">${emoji}</span>
                                <div class="weather-temp-block">
                                    <div class="weather-temp-value">${tempC}°C <span class="weather-temp-sub">/ ${tempF}°F</span></div>
                                    <div class="weather-condition-text">${condition}</div>
                                </div>
                            </div>
                            <div class="weather-feels-like">Feels like <strong>${feelsC}°C (${feelsF}°F)</strong></div>
                        </div>

                        <div class="climate-chips-grid">
                            <div class="climate-chip">
                                <span class="chip-icon">🌡️</span>
                                <div class="chip-content">
                                    <span class="chip-label">High / Low</span>
                                    <span class="chip-val">${maxC}° / ${minC}°C</span>
                                </div>
                            </div>
                            <div class="climate-chip">
                                <span class="chip-icon">💧</span>
                                <div class="chip-content">
                                    <span class="chip-label">Humidity</span>
                                    <span class="chip-val">${humidity}%</span>
                                </div>
                            </div>
                            <div class="climate-chip">
                                <span class="chip-icon">💨</span>
                                <div class="chip-content">
                                    <span class="chip-label">Wind Speed</span>
                                    <span class="chip-val">${wind} km/h</span>
                                </div>
                            </div>
                            <div class="climate-chip">
                                <span class="chip-icon">🌧️</span>
                                <div class="chip-content">
                                    <span class="chip-label">Rain Chance</span>
                                    <span class="chip-val">${rain}%</span>
                                </div>
                            </div>
                        </div>

                        ${embedUrl ? `
                        <div class="map-embed-wrapper">
                            <iframe 
                                class="map-embed-iframe" 
                                src="${embedUrl}" 
                                title="Interactive Map of ${locDisplay}"
                                loading="lazy"
                            ></iframe>
                        </div>
                        ` : ''}

                        <div class="weather-card-actions">
                            <a href="${gMapsUrl}" target="_blank" rel="noopener noreferrer" class="gmaps-action-btn">
                                <span class="btn-gmaps-icon">🗺️</span>
                                <span>Open in Google Maps</span>
                                <svg class="external-link-arrow" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                                    <polyline points="15 3 21 3 21 9"></polyline>
                                    <line x1="10" y1="14" x2="21" y2="3"></line>
                                </svg>
                            </a>
                        </div>
                    </div>
                `;
            }

            let musicHtml = '';
            if (meta && meta.is_music && meta.music) {
                musicHtml = `
                    <div class="music-player-card">
                        <div class="music-card-header">
                            <div class="music-equalizer">
                                <span class="eq-bar"></span>
                                <span class="eq-bar"></span>
                                <span class="eq-bar"></span>
                                <span class="eq-bar"></span>
                            </div>
                            <div class="music-card-info">
                                <div class="music-track-title">${escapeHtml(meta.music.title)}</div>
                                <div class="music-track-sub">YouTube Audio Stream</div>
                            </div>
                        </div>
                        <audio controls autoplay class="kitty-audio-player" src="${meta.music.stream_url}"></audio>
                        <div class="music-card-actions">
                            <button type="button" class="card-btn-pause" onclick="window.toggleKittyMusic()">⏸️ Pause / Resume</button>
                            <button type="button" class="card-btn-stop" onclick="window.stopKittyMusic()">⏹️ Stop Music</button>
                        </div>
                    </div>
                `;
            }

            rowDiv.innerHTML = `
                <div class="message-bubble ai-bubble">
                    <div class="ai-text-content">${escapeHtml(text)}</div>
                    ${weatherMapHtml}
                    ${musicHtml}
                </div>
                <div class="message-timestamp">${getCurrentTimeString()}</div>
            `;
        }

        chatMessages.appendChild(rowDiv);
        scrollToBottom();
    }

    // Show animated typing indicator
    function showTypingIndicator() {
        if (!chatMessages) return;
        removeTypingIndicator(); // Ensure no duplicates

        const indicator = document.createElement('div');
        indicator.id = 'typing-indicator';
        indicator.classList.add('message-row', 'ai-row');
        indicator.innerHTML = `
            <div class="typing-bubble" title="Hello Kitty is thinking...">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
        `;
        chatMessages.appendChild(indicator);
        scrollToBottom();
    }

    // Remove animated typing indicator
    function removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    // Main handler: Send user message to Flask /chat route
    async function handleSendMessage(messageText) {
        if (isSubmitting) {
            console.warn('[Hello Kitty Client] Request already in progress, ignoring duplicate send.');
            return;
        }

        const cleanText = (typeof messageText === 'string' ? messageText : (userInput ? userInput.value : '')).trim();
        if (!cleanText) {
            if (userInput) userInput.focus();
            return;
        }

        // Ensure chat container is revealed if user triggers a prompt
        if (chatContainer && !chatContainer.classList.contains('chat-active')) {
            openChatView();
        }

        isSubmitting = true;

        // 1. Render User Bubble immediately
        appendMessage('user', cleanText);
        if (userInput) {
            userInput.value = '';
        }

        // 2. UI State: Disable send button & show typing indicator
        if (sendBtn) sendBtn.disabled = true;
        showTypingIndicator();

        const payload = { message: cleanText };
        console.log('[Hello Kitty Client] Sending POST /chat with payload:', payload);

        // Set a 45-second timeout to avoid indefinite hanging on slow network/LLM calls
        const controller = new AbortController();
        const timeoutTimer = setTimeout(() => controller.abort(), 45000);

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(payload),
                signal: controller.signal
            });

            clearTimeout(timeoutTimer);

            // Safely parse JSON or text response
            let responseData;
            const rawText = await response.text();
            try {
                responseData = JSON.parse(rawText);
            } catch (parseErr) {
                console.warn('[Hello Kitty Client] Non-JSON response received:', rawText);
                responseData = { reply: rawText || `Server returned HTTP ${response.status}` };
            }

            console.log('[Hello Kitty Client] Response received:', response.status, responseData);
            removeTypingIndicator();

            if (response.ok && responseData.reply) {
                appendMessage('ai', responseData.reply, responseData);
                // Speak the reply aloud like Alexa!
                speakAloud(responseData.reply);
            } else {
                const errorText = responseData.reply || `Error (${response.status}): Could not get reply from Hello Kitty.`;
                appendMessage('ai', errorText);
                speakAloud(errorText);
            }

        } catch (err) {
            clearTimeout(timeoutTimer);
            removeTypingIndicator();
            console.error('[Hello Kitty Client] Fetch failure:', err);

            const errMessage = (err.name === 'AbortError')
                ? '⚠️ Request timed out. Hello Kitty took too long to reply. Please try again.'
                : '⚠️ Connection error: Could not connect to the Hello Kitty server. Please verify web/app.py is running.';

            appendMessage('ai', errMessage);
            speakAloud(errMessage);
        } finally {
            isSubmitting = false;
            if (sendBtn) sendBtn.disabled = false;
            if (userInput) {
                userInput.disabled = false;
                userInput.focus();
            }
        }
    }

    // Form submit event (supports Enter key submission)
    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleSendMessage();
        });
    }

    // Quick suggestion buttons handler exposed globally for inline onclick
    window.sendQuickPrompt = function(promptText) {
        console.log('[Hello Kitty Client] Quick prompt selected:', promptText);
        handleSendMessage(promptText);
    };

    // Clear Chat button handler
    if (clearBtn) {
        clearBtn.addEventListener('click', async function() {
            if (confirm('Are you sure you want to clear the conversation history?')) {
                try {
                    console.log('[Hello Kitty Client] Requesting /clear endpoint...');
                    const resp = await fetch('/clear', { method: 'POST' });
                    const resJson = await resp.json();
                    console.log('[Hello Kitty Client] Clear response:', resJson);

                    if (chatMessages) {
                        chatMessages.innerHTML = '';
                    }
                    const clearedMsg = 'Chat history has been cleared! What would you like to talk about next?';
                    appendMessage('ai', clearedMsg);
                    speakAloud(clearedMsg);
                } catch (err) {
                    console.error('[Hello Kitty Client] Failed to clear history:', err);
                }
            }
        });
    }

    // --- Mobile Connect Modal Logic ---
    function openMobileModal() {
        if (mobileModal && mobileModalBackdrop) {
            mobileModal.classList.remove('modal-hidden');
            mobileModalBackdrop.classList.remove('modal-hidden');
        }
    }

    function closeMobileModal() {
        if (mobileModal && mobileModalBackdrop) {
            mobileModal.classList.add('modal-hidden');
            mobileModalBackdrop.classList.add('modal-hidden');
        }
    }

    if (mobileConnectBtn) {
        mobileConnectBtn.addEventListener('click', openMobileModal);
    }
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', closeMobileModal);
    }
    if (mobileModalBackdrop) {
        mobileModalBackdrop.addEventListener('click', closeMobileModal);
    }

    if (copyUrlBtn && mobileUrlInput) {
        copyUrlBtn.addEventListener('click', async function() {
            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(mobileUrlInput.value);
                } else {
                    mobileUrlInput.select();
                    document.execCommand('copy');
                }
                if (copyUrlIcon) copyUrlIcon.textContent = '✅';
                if (copyUrlText) copyUrlText.textContent = 'Copied!';
                setTimeout(() => {
                    if (copyUrlIcon) copyUrlIcon.textContent = '📋';
                    if (copyUrlText) copyUrlText.textContent = 'Copy';
                }, 2000);
            } catch (e) {
                mobileUrlInput.select();
                document.execCommand('copy');
                if (copyUrlIcon) copyUrlIcon.textContent = '✅';
                if (copyUrlText) copyUrlText.textContent = 'Copied!';
                setTimeout(() => {
                    if (copyUrlIcon) copyUrlIcon.textContent = '📋';
                    if (copyUrlText) copyUrlText.textContent = 'Copy';
                }, 2000);
            }
        });
    }

    // Mobile Virtual Keyboard Scroll Adjustment
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', () => {
            if (chatMessages) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        });
    }

    // Initial music status check on load
    fetch('/music/status')
        .then(r => r.json())
        .then(data => {
            if (data && (data.is_playing || data.is_paused)) {
                updateMusicBar(data);
            }
        })
        .catch(() => {});

    console.log('[Hello Kitty Client] Alexa-style voice interface ready!');
})();
