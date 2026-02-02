import { useState, useEffect, useRef } from 'react';

const useVoiceRecognition = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [finalTranscript, setFinalTranscript] = useState('');
  const recognitionRef = useRef(null);
  const finalTranscriptRef = useRef('');

  useEffect(() => {
    if (!('webkitSpeechRecognition' in window)) {
      console.error("Web Speech API is not supported by this browser.");
      return;
    }

    const recognition = new window.webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      let interim = '';
      let newlyFinal = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const text = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          newlyFinal += text;
        } else {
          interim += text;
        }
      }
      if (newlyFinal) {
        finalTranscriptRef.current += newlyFinal;
        setFinalTranscript(finalTranscriptRef.current);
      }
      const combined = `${finalTranscriptRef.current}${interim}`;
      setTranscript(combined);
    };
    
    recognition.onerror = (event) => {
      console.error("Speech recognition error", event.error);
    };
    recognition.onend = () => {
      setIsRecording(false);
    };

    recognitionRef.current = recognition;
  }, []);

  const startRecording = () => {
    if (recognitionRef.current) {
      finalTranscriptRef.current = '';
      setFinalTranscript('');
      setTranscript('');
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsRecording(false);
    }
    const text = finalTranscriptRef.current;
    finalTranscriptRef.current = '';
    setFinalTranscript('');
    setTranscript('');
    return text;
  };
  
  const speak = (text) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en-US';
      window.speechSynthesis.speak(utterance);
    } else {
      console.error("Web Speech Synthesis is not supported by this browser.");
    }
  };

  return { isRecording, transcript, finalTranscript, startRecording, stopRecording, speak };
};

export default useVoiceRecognition;
