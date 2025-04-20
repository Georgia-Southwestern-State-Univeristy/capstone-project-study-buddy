using Microsoft.AspNetCore.SignalR;
using Microsoft.CognitiveServices.Speech;
using Microsoft.CognitiveServices.Speech.Audio;
using SpeechTranslator.Hubs;
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading.Tasks;

namespace SpeechTranslator.Services
{
    public class SpeechToTextService
    {
        private readonly SpeechConfig _speechConfig;
        private readonly TranslationService _translationService;
        private SpeechRecognizer? _speechRecognizer;
        private SpeechSynthesizer? _speechSynthesizer;
        private bool _isListening;

        // Add properties to accumulate text
        private readonly StringBuilder _accumulatedOriginalText = new();
        private readonly StringBuilder _accumulatedTranslatedText = new();

        // Add property to access the accumulated texts
        public (string Original, string Translated) AccumulatedTexts => 
            (_accumulatedOriginalText.ToString(), _accumulatedTranslatedText.ToString());

        public SpeechToTextService(string speechEndpoint, string speechKey)
        {
            if (string.IsNullOrEmpty(speechEndpoint))
                throw new ArgumentNullException(nameof(speechEndpoint));
            if (string.IsNullOrEmpty(speechKey))
                throw new ArgumentNullException(nameof(speechKey));
                
            _speechConfig = SpeechConfig.FromEndpoint(new Uri(speechEndpoint), speechKey);
            
            // Get environment variables with proper null checking and defaults
            string translatorApiKey = Environment.GetEnvironmentVariable("TRANSLATOR_API_KEY") 
                ?? throw new ArgumentException("TRANSLATOR_API_KEY environment variable is not set");
            string translatorEndpoint = Environment.GetEnvironmentVariable("TRANSLATOR_ENDPOINT") 
                ?? "https://api.cognitive.microsofttranslator.com/";
            string translatorRegion = Environment.GetEnvironmentVariable("TRANSLATOR_REGION") 
                ?? throw new ArgumentException("TRANSLATOR_REGION environment variable is not set");
            
            _translationService = new TranslationService(
                translatorApiKey,
                translatorEndpoint,
                translatorRegion
            );
            _isListening = false;
        }

        public async Task<string> ConvertSpeechToTextAsync()
        {
            using var recognizer = new SpeechRecognizer(_speechConfig);

            Console.WriteLine("Speak into your microphone.");
            var result = await recognizer.RecognizeOnceAsync();

            if (result.Reason == ResultReason.RecognizedSpeech)
            {
                return result.Text;
            }

            throw new Exception("Speech could not be recognized.");
        }

        public async Task<string> ConvertSpeechToTextAsync(string audioFilePath)
        {
            using var audioConfig = AudioConfig.FromWavFileInput(audioFilePath);
            using var recognizer = new SpeechRecognizer(_speechConfig, audioConfig);

            Console.WriteLine("Processing audio file...");
            var result = await recognizer.RecognizeOnceAsync();

            if (result.Reason == ResultReason.RecognizedSpeech)
            {
                return result.Text;
            }

            throw new Exception("Speech could not be recognized from the audio file.");
        }

        public async Task<string> ConvertSpeechToTextFromVideoAsync(string videoFilePath)
        {
            // Extract audio from video file (placeholder for actual implementation)
            string extractedAudioPath = ExtractAudioFromVideo(videoFilePath);

            // Use the existing audio file method
            return await ConvertSpeechToTextAsync(extractedAudioPath);
        }

        private string ExtractAudioFromVideo(string videoFilePath)
        {
            string audioFilePath = Path.ChangeExtension(videoFilePath, ".wav");

            // Construct the FFmpeg command
            string ffmpegCommand = $"ffmpeg -i \"{videoFilePath}\" -q:a 0 -map a \"{audioFilePath}\" -y";

            // Execute the command
            var process = new System.Diagnostics.Process
            {
                StartInfo = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = "cmd.exe",
                    Arguments = $"/C {ffmpegCommand}",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                }
            };

            process.Start();
            process.WaitForExit();

            if (process.ExitCode != 0)
            {
                throw new Exception("Failed to extract audio from video. Ensure FFmpeg is installed and accessible from the command line.");
            }

            return audioFilePath;
        }

        public async IAsyncEnumerable<(string Original, string Translated)> GetSpeechStreamAsync(string sourceLanguage, string targetLanguage)
        {
            _speechRecognizer = new SpeechRecognizer(_speechConfig);
            _speechSynthesizer = new SpeechSynthesizer(_speechConfig);

            // Clear previous accumulated text when starting a new session
            _accumulatedOriginalText.Clear();
            _accumulatedTranslatedText.Clear();

            var translationPairs = new Queue<(string Original, string Translated)>();
            _isListening = true;

            // Invoke the translation service for interim results
            _speechRecognizer.Recognizing += async (s, e) =>
            {
                if (!string.IsNullOrWhiteSpace(e.Result.Text))
                {
                    Console.WriteLine($"Interim Recognized: {e.Result.Text}");
                    
                    // We're not adding interim results to the queue
                }
            };

            _speechRecognizer.Recognized += async (s, e) =>
            {
                if (!string.IsNullOrWhiteSpace(e.Result.Text))
                {
                    string originalText = e.Result.Text;
                    
                    var translationStream = _translationService.TranslateTextStreamAsync(sourceLanguage, targetLanguage, GetSingleTextStream(originalText));
                    await foreach (var translatedText in translationStream)
                    {
                        Console.WriteLine($"Original: {originalText}");
                        Console.WriteLine($"Translated: {translatedText}");
                        
                        // Accumulate the text
                        if (_accumulatedOriginalText.Length > 0)
                        {
                            _accumulatedOriginalText.Append(" ");
                            _accumulatedTranslatedText.Append(" ");
                        }
                        _accumulatedOriginalText.Append(originalText);
                        _accumulatedTranslatedText.Append(translatedText);
                        
                        // Store both original and translated text
                        translationPairs.Enqueue((originalText, translatedText));
                    }
                }
            };

            await _speechRecognizer.StartContinuousRecognitionAsync();

            while (_isListening)
            {
                while (translationPairs.Count > 0)
                {
                    yield return translationPairs.Dequeue();
                }

                await Task.Delay(30); // Allow recognition to continue
            }

            await _speechRecognizer.StopContinuousRecognitionAsync();
            yield break;

            static async IAsyncEnumerable<string> GetSingleTextStream(string text)
            {
                yield return text;
                await Task.CompletedTask;
            }
        }

        public async Task StopListeningAsync()
        {
            _isListening = false;

            if (_speechRecognizer != null)
            {
                await _speechRecognizer.StopContinuousRecognitionAsync();
                _speechRecognizer.Dispose();
            }

            if (_speechSynthesizer != null)
            {
                _speechSynthesizer.Dispose();
            }
        }

        // Add method to get the full accumulated text
        public (string Original, string Translated) GetFullText()
        {
            return AccumulatedTexts;
        }
    }
}