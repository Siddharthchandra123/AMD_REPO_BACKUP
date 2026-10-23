import { useEffect, useRef, useState } from 'react';
import {
  AudioLines, Mic, Square, Send, LoaderCircle,
  Volume2, Bot, User, Cpu, RotateCcw, Play, Pause
} from 'lucide-react';

type Message = {
  role: 'user' | 'assistant';
  text: string;
};

type VoiceResponse = {
  transcript: string;
  answer: string;
  audio_base64: string;
  audio_format: string;
};

const SESSION_ID = crypto.randomUUID();

function playAudio(base64: string) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  const blob = new Blob([bytes], { type: 'audio/wav' });
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.onended = () => URL.revokeObjectURL(url);
  audio.onerror = () => URL.revokeObjectURL(url);
  audio.play().catch(console.error);
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(true);
  const [recording, setRecording] = useState(false);
  const [status, setStatus] = useState('Ready to talk');
  const [error, setError] = useState('');

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const audioCache = useRef<Map<number, string>>(new Map());
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  const [playingIndex, setPlayingIndex] = useState<number | null>(null);
  const [paused, setPaused] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState<number | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);


  function stopCurrentAudio() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }

    setPlayingIndex(null);
    setPaused(false);
  }

  function playCachedAudio(index: number, base64: string) {
    stopCurrentAudio();

    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);

    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }

    const blob = new Blob([bytes], { type: 'audio/wav' });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);

    audioUrlRef.current = url;
    audioRef.current = audio;

    audio.onended = () => {
      stopCurrentAudio();
    };

    audio.onerror = () => {
      stopCurrentAudio();
      setError('Audio playback failed.');
    };

    setPlayingIndex(index);
    setPaused(false);

    audio.play().catch(err => {
      console.error('Audio playback error:', err);
      stopCurrentAudio();
      setError('Browser blocked audio playback. Click Play again.');
    });
  }

  async function replayMessage(index: number, text: string) {
    if (loadingAudio !== null) return;

    if (playingIndex === index && audioRef.current) {
      if (paused) {
        await audioRef.current.play();
        setPaused(false);
      } else {
        audioRef.current.pause();
        setPaused(true);
      }
      return;
    }

    const cached = audioCache.current.get(index);

    if (cached) {
      playCachedAudio(index, cached);
      return;
    }

    setLoadingAudio(index);
    setError('');

    try {
      const response = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });

      if (!response.ok) {
        throw new Error(`TTS HTTP ${response.status}`);
      }

      const data = await response.json();

      if (!data.audio_base64) {
        throw new Error('No audio returned');
      }

      audioCache.current.set(index, data.audio_base64);
      playCachedAudio(index, data.audio_base64);

    } catch (err) {
      console.error('TTS failed:', err);
      setError('Unable to generate speech.');
    } finally {
      setLoadingAudio(null);
    }
  }

  function replayFromStart(index: number, text: string) {
    if (playingIndex === index && audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.play().then(() => {
        setPaused(false);
      }).catch(console.error);
    } else {
      void replayMessage(index, text);
    }
  }

  async function sendText() {
    const text = input.trim();
    if (!text || busy) return;

    setInput('');
    setError('');
    setBusy(true);
    setStatus('Thinking...');
    setMessages(prev => [...prev, { role: 'user', text }]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          session_id: SESSION_ID
        })
      });

      if (!response.ok) throw new Error(`API error: ${response.status}`);

      const data = await response.json();
      setMessages(prev => [
        ...prev,
        { role: 'assistant', text: data.answer }
      ]);
      setStatus('Ready to talk');

      if (autoSpeak && data.answer) {
        setStatus('Generating speech...');

        try {
          const ttsResponse = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: data.answer })
          });

          if (!ttsResponse.ok) {
            throw new Error(`TTS error: ${ttsResponse.status}`);
          }

          const speech = await ttsResponse.json();

          if (speech.audio_base64) {
            playAudio(speech.audio_base64);
          }
        } catch (ttsError) {
          console.error('Speech generation failed:', ttsError);
        }

        setStatus('Ready to talk');
      }
    } catch (err) {
      setError(String(err));
      setStatus('Request failed');
    } finally {
      setBusy(false);
    }
  }

  async function startRecording() {
    if (busy || recording) return;

    setError('');

    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone requires HTTPS or localhost.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true
      });

      const preferredTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/mp4'
      ];

      const mimeType = preferredTypes.find(
        type => MediaRecorder.isTypeSupported(type)
      );

      const recorder = new MediaRecorder(
        stream,
        mimeType ? { mimeType } : undefined
      );

      chunksRef.current = [];
      streamRef.current = stream;
      recorderRef.current = recorder;

      recorder.ondataavailable = event => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        streamRef.current = null;

        const type = recorder.mimeType || 'audio/webm';
        const extension = type.includes('mp4') ? 'mp4' : 'webm';

        const blob = new Blob(chunksRef.current, { type });
        chunksRef.current = [];

        if (!blob.size) {
          setError('No audio was recorded.');
          setStatus('Ready to talk');
          return;
        }

        await sendVoice(blob, extension);
      };

      recorder.start();
      setRecording(true);
      setStatus('Listening...');
    } catch (err) {
      streamRef.current?.getTracks().forEach(track => track.stop());
      streamRef.current = null;
      setError('Microphone unavailable: ' + String(err));
      setStatus('Microphone error');
    }
  }

  function stopRecording() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== 'recording') return;

    setRecording(false);
    setStatus('Processing speech...');
    recorder.stop();
  }

  async function sendVoice(blob: Blob, extension: string) {
    setBusy(true);
    setError('');

    try {
      const form = new FormData();
      form.append('file', blob, `recording.${extension}`);

      const response = await fetch('/api/voice', {
        method: 'POST',
        body: form
      });

      if (!response.ok) {
        throw new Error(`Voice API error: ${response.status}`);
      }

      const data: VoiceResponse = await response.json();

      setMessages(prev => [
        ...prev,
        { role: 'user', text: data.transcript },
        { role: 'assistant', text: data.answer }
      ]);

      setStatus('Playing response...');
      playAudio(data.audio_base64);
      setStatus('Ready to talk');
    } catch (err) {
      setError(String(err));
      setStatus('Voice request failed');
    } finally {
      setBusy(false);
    }
  }

  function clearChat() {
    setMessages([]);
    setError('');
  }

  return (
    <div className="app">
      <button
        type="button"
        onClick={() => setAutoSpeak(value => !value)}
        title={autoSpeak ? 'Disable automatic speech' : 'Enable automatic speech'}
        style={{
          position: 'fixed',
          top: 16,
          right: 16,
          zIndex: 1000,
          padding: '10px 14px',
          borderRadius: 10,
          cursor: 'pointer',
          background: autoSpeak ? '#2563eb' : '#475569',
          color: 'white',
          border: 'none'
        }}
      >
        {autoSpeak ? '🔊 Voice ON' : '🔇 Voice OFF'}
      </button>

      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><AudioLines size={25} /></div>
          <div>
            <strong>MI300X Voice</strong>
            <small>Self-hosted AI assistant</small>
          </div>
        </div>

        <div className="system-panel">
          <span className="eyebrow">AI INFRASTRUCTURE</span>
          <div className="system-item"><Cpu size={17} /> AMD Instinct MI300X</div>
          <div className="system-item"><Bot size={17} /> Qwen2.5-3B</div>
          <div className="system-item"><Mic size={17} /> Whisper ASR</div>
          <div className="system-item"><Volume2 size={17} /> Kokoro TTS</div>
        </div>

        <button className="clear-btn" onClick={clearChat}>
          <RotateCcw size={16} /> Clear conversation
        </button>

        <div className="sidebar-footer">
          <span className="status-dot" />
          Backend connected via FastAPI
        </div>
      </aside>

      <main className="main">
        <header className="header">
          <div>
            <h1>Voice Assistant</h1>
            <p>Powered by AMD Instinct MI300X</p>
          </div>
          <span className="header-tag">SELF HOSTED</span>
        </header>

        <section className="conversation">
          {messages.length === 0 && (
            <div className="welcome">
              <div className="orb"><AudioLines size={45} /></div>
              <h2>How can I help you today?</h2>
              <p>Start a conversation using your microphone or type a message.</p>
            </div>
          )}

          {messages.map((message, index) => (
            <div className={`message ${message.role}`} key={index}>
              <div className="avatar">
                {message.role === 'assistant'
                  ? <Bot size={19} />
                  : <User size={19} />}
              </div>
              <div>
                <div className="bubble">{message.text}</div>

                {message.role === 'assistant' && (
                  <div
                    style={{
                      display: 'flex',
                      gap: 8,
                      marginTop: 8,
                      alignItems: 'center'
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => replayMessage(index, message.text)}
                      disabled={loadingAudio === index}
                      title={playingIndex === index
                        ? paused ? 'Resume' : 'Pause'
                        : 'Play'}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '6px 10px',
                        borderRadius: 8,
                        cursor: 'pointer'
                      }}
                    >
                      {loadingAudio === index
                        ? <LoaderCircle size={15} className="spin" />
                        : playingIndex === index && !paused
                          ? <Pause size={15} />
                          : <Play size={15} />}
                      {loadingAudio === index
                        ? 'Loading'
                        : playingIndex === index && !paused
                          ? 'Pause'
                          : paused && playingIndex === index
                            ? 'Resume'
                            : 'Play'}
                    </button>

                    <button
                      type="button"
                      onClick={() => replayFromStart(index, message.text)}
                      disabled={loadingAudio === index}
                      title="Replay from beginning"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '6px 10px',
                        borderRadius: 8,
                        cursor: 'pointer'
                      }}
                    >
                      <RotateCcw size={15} />
                      Replay
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {busy && (
            <div className="working">
              <LoaderCircle size={17} className="spin" />
              Processing your request...
            </div>
          )}

          <div ref={bottomRef} />
        </section>

        <div className="controls">
          {error && <div className="error">{error}</div>}

          <div className="voice-controls">
            <button
              className={`mic-button ${recording ? 'recording' : ''}`}
              onClick={recording ? stopRecording : startRecording}
              disabled={busy}
              aria-label={recording ? 'Stop recording' : 'Start recording'}
            >
              {recording ? <Square size={25} /> : <Mic size={29} />}
            </button>
            <div className="voice-status">
              <strong>{status}</strong>
              <small>
                {recording
                  ? 'Click the button to stop recording'
                  : 'Click the microphone to speak'}
              </small>
            </div>
          </div>

          <div className="text-input">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') sendText();
              }}
              placeholder="Ask anything..."
              disabled={busy || recording}
            />
            <button
              onClick={sendText}
              disabled={busy || recording || !input.trim()}
              aria-label="Send message"
            >
              <Send size={20} />
            </button>
          </div>

          <p className="footnote">
            Your AI models and inference run on your own infrastructure.
          </p>
        </div>
      </main>
    </div>
  );
}
