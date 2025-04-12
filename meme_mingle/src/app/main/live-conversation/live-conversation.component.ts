import {
  Component,
  OnInit,
  OnDestroy,
  ViewChild,
  ElementRef,
} from '@angular/core';
import { AppService } from '../../app.service';
import { Subscription } from 'rxjs';
import { CommonModule } from '@angular/common';
import { environment } from '../../shared/environments/environment';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { FormsModule } from '@angular/forms';
import { MarkdownModule } from 'ngx-markdown';
import { HttpClientModule } from '@angular/common/http';
import { marked } from 'marked';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MatFormFieldModule } from '@angular/material/form-field'; 
import { MatSelectModule } from '@angular/material/select'; 
import {
  trigger,
  style,
  animate,
  transition,
} from '@angular/animations';
import { ChatService } from './chat.service';
interface ConversationMessage {
  sender: 'User' | 'Mentor';
  message: string;
  audioUrl?: string;
  imageUrl?: string;
  file?: { name: string; type: string };
  timestamp: Date;
  htmlContent?: SafeHtml;
}

interface IWindow extends Window {
  SpeechRecognition: any;
  webkitSpeechRecognition: any;
}

interface HistoricalFigure {
  display: string;
  value: string;
  field: string;
  imageUrl?: string; // Add the imageUrl property
}

@Component({
  selector: 'app-live-conversation',
  standalone: true,
  imports: [
    CommonModule,
    MatTooltipModule,
    MatIconModule,
    MatProgressBarModule,
    MatButtonModule,
    FormsModule,
    HttpClientModule, 
    MarkdownModule, 
    MatFormFieldModule, 
    MatSelectModule,    
  ],
  templateUrl: './live-conversation.component.html',
  styleUrls: ['./live-conversation.component.scss'],
  animations: [
    trigger('messageAnimation', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(20px)' }),
        animate(
          '300ms ease-out',
          style({ opacity: 1, transform: 'translateY(0)' })
        ),
      ]),
    ]),
    trigger('fadeInOut', [
      transition(':enter', [
        style({ opacity: 0 }),
        animate('300ms ease-in', style({ opacity: 1 })),
      ]),
      transition(':leave', [
        animate('300ms ease-out', style({ opacity: 0 })),
      ]),
    ]),
    trigger('buttonClick', [
      transition('* => active', [
        animate(
          '200ms',
          style({ transform: 'scale(0.9)', offset: 0.5 })
        ),
        animate('200ms', style({ transform: 'scale(1)' })),
      ]),
    ]),
    trigger('overlayAnimation', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(-20%)' }),
        animate(
          '500ms ease-out',
          style({ opacity: 1, transform: 'translateY(0)' })
        ),
      ]),
      transition(':leave', [
        animate(
          '500ms ease-in',
          style({ opacity: 0, transform: 'translateY(-20%)' })
        ),
      ]),
    ]),
    trigger('statusAnimation', [
      transition(':enter', [
        style({ opacity: 0 }),
        animate('300ms ease-in', style({ opacity: 1 })),
      ]),
      transition(':leave', [
        animate('300ms ease-out', style({ opacity: 0 })),
      ]),
    ]),
  ],
})
export class LiveConversationComponent implements OnInit, OnDestroy {
  recognition: any;
  isListening = false;
  isProcessing = false;
  isPlaying = false;
  conversation: ConversationMessage[] = [];
  userId = 'default_user';
  chatId = '1';
  turnId = 0;
  audio = new Audio();
  subscriptions = new Subscription();
  showOverlay = true;
  backendUrl = environment.baseUrl;
  isDarkMode = false;
  isMuted = false;
  userStopped = false;
  userProfilePicture: string = '';
  userInputText: string = '';
  selectedFile: File | null = null;
  selectedRole: string = ''; 
  selectedRoleImageUrl: string = 'assets/img/banner.png';
  preferredLanguage: string = 'en';
  translatedTexts: { [key: string]: string } = {};
  roles: HistoricalFigure[] = [];
  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;

  constructor(private appService: AppService, private chatService: ChatService,private sanitizer: DomSanitizer) {}

  ngOnInit(): void {
    this.initializeTheme();
    this.fetchUserProfile();
    this.userId = localStorage.getItem('user_id') || 'default_user';
    this.chatId = this.chatService.getChatId() || this.chatService.generateChatId();
    this.preferredLanguage = localStorage.getItem('preferredLanguage') || 'en';

    if (this.preferredLanguage !== 'en') {
      this.translateContent(this.preferredLanguage);
    }

    const windowObj = window as unknown as IWindow;
    const SpeechRecognition =
      windowObj.SpeechRecognition || windowObj.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert(
        'Your browser does not support Speech Recognition. Please try a different browser.'
      );
      return;
    }

    this.recognition = new SpeechRecognition();
    this.recognition.lang = 'en-US';
    this.recognition.continuous = false;
    this.recognition.interimResults = false;

    this.recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript.trim();
      if (transcript) {
        this.addMessage('User', transcript);
        this.processUserInput(transcript);
      }
    };

    this.recognition.onerror = (event: any) => {
      console.error('Speech Recognition Error:', event.error);
      this.isListening = false;
      this.isProcessing = false;
    };

    this.recognition.onend = () => {
      this.isListening = false;
      if (!this.isProcessing && !this.userStopped) {
        this.startListening();
      }
    };
  }

  // Translate content to the target language
  private translateContent(targetLanguage: string) {
    const elementsToTranslate = document.querySelectorAll('[data-translate]');
    const textsToTranslate = Array.from(elementsToTranslate).map(
      (el) => el.textContent?.trim() || ''
    );

    // Include additional texts that are not in data-translate attributes
    const additionalTexts = [
    'Welcome to AI Chat',
    'Choose a mentor to inspire your conversation.',
    'Select Your Mentor',
    'Start Conversation',
    'Type your message here...',
    'Pause Listening',
    'Resume Listening',
    'File upload',
    'New Conversation',
    'send message',
    'Unmute',
    'Mute',
    'Replay Audio',
    'AI is speaking...',
    'AI is listening...',
    'Want more mentors? Add your "interested subjects" in "User Profile > Academic tab."',
  ];
    const allTextsToTranslate = [...textsToTranslate, ...additionalTexts];

    this.appService
      .translateTexts(allTextsToTranslate, targetLanguage)
      .subscribe((response) => {
        const translations = response.translations;

        // Translate texts from data-translate elements
        elementsToTranslate.forEach((element, index) => {
          const originalText = textsToTranslate[index];
          this.translatedTexts[originalText] = translations[index];

          // Update directly if it's a regular DOM element
          if (!(element.tagName.startsWith('MAT-'))) {
            element.textContent = translations[index];
          }
        });

        // Handle additional texts
        additionalTexts.forEach((text, index) => {
          const translatedText = translations[textsToTranslate.length + index];
          this.translatedTexts[text] = translatedText;
        });
      });
  }

  finalizeChat(): void {
    if (
      confirm(
        'Are you sure you want to end the conversation? This will finalize the chat session.'
      )
    ) {
      this.isProcessing = true;
      const finalizeSub = this.appService
        .finalizeChat(this.userId, this.chatId)
        .subscribe({
          next: () => {
            this.addMessage(
              'Mentor',
              'Thank you for chatting! If you need further assistance, feel free to start a new conversation.'
            );
            this.isProcessing = false;
            this.stopListening();
            this.showOverlay = true;
            this.chatService.clearChatId();
          },
          error: (error: any) => {
            console.error('Error finalizing chat:', error);
            this.isProcessing = false;
          },
        });
      this.subscriptions.add(finalizeSub);
    }
  }

  stopListening(): void {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
      this.isListening = false;
      this.userStopped = true;
    }
  }

  startListening(): void {
    if (this.isListening || this.isProcessing || this.isPlaying) return;
    
    // Check if running on iOS
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    
    try {
      this.recognition.start();
      this.isListening = true;
      this.userStopped = false;
      
      // For iOS devices, set a timeout to verify if recognition is actually working
      if (isIOS || isSafari) {
        setTimeout(() => {
          if (this.isListening) {
            // Try to restart recognition to ensure it's not stuck
            try {
              this.recognition.stop();
              setTimeout(() => {
                try {
                  this.recognition.start();
                } catch (e) { /* Ignore errors */ }
              }, 300);
            } catch (e) { /* Ignore errors */ }
          }
        }, 5000);
      }
    } catch (error) {
      console.error('Failed to start recognition:', error);
      this.isListening = false;
    }
  }

  toggleListening(): void {
    if (this.isListening) {
      this.stopListening();
    } else {
      this.startListening();
    }
  }

  toggleMute(): void {
    this.isMuted = !this.isMuted;
    this.audio.muted = this.isMuted;
  }

  playAudio(url: string): void {
    if (!url) return;
    this.isPlaying = true;
    this.audio.src = url;
    this.audio.load();
    this.audio.muted = this.isMuted;

    this.audio
      .play()
      .then(() => {
        if (this.isListening) {
          this.recognition.stop();
          this.isListening = false;
        }
      })
      .catch((err) => {
        console.error('Audio Playback Error:', err);
        this.isPlaying = false;
      });

    this.audio.onended = () => {
      this.isPlaying = false;
      if (!this.isMuted) {
        this.startListening();
      }
    };
  }

  unlockAudio(): void {
    // First hide the overlay and initialize conversation
    this.showOverlay = false;
    
    // Check if running on iOS/Safari
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    const isIOSSafari = isIOS || isSafari;
    
    // For iOS, we'll use a different approach
    if (isIOSSafari) {
      console.log('iOS/Safari detected, using special initialization');
      
      // Add a notification for users about iOS limitations
      this.addMessage('Mentor', 
        'Welcome! Voice recognition has limited functionality on iOS devices. ' +
        'If voice doesn\'t work after granting permission, please use text input instead.');
      
      // Initialize conversation right away to avoid delays
      this.initializeConversation();
      
      // Try to unlock audio capabilities with user interaction
      const silentAudio = new Audio();
      silentAudio.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=';
      
      silentAudio.play()
        .then(() => {
          silentAudio.pause();
          console.log('Audio context unlocked successfully');
          
          // Initialize speech recognition with timeout protection
          this.initializeIOSSpeechRecognition();
        })
        .catch((error) => {
          console.warn('Audio initialization error:', error);
        });
    } else {
      // Standard approach for non-iOS browsers
      const silentAudio = new Audio();
      silentAudio.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA=';
      
      silentAudio.play()
        .then(() => {
          silentAudio.pause();
          this.initializeConversation();
          setTimeout(() => this.startListening(), 1000);
        })
        .catch(() => {
          this.initializeConversation();
        });
    }
  }
  
  // New method specifically for handling iOS speech recognition
  initializeIOSSpeechRecognition(): void {
    // First make sure we have a clean state
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) { /* Ignore errors */ }
    }
  
    // Reinitialize recognition with iOS optimized settings
    const windowObj = window as unknown as IWindow;
    const SpeechRecognition = windowObj.SpeechRecognition || windowObj.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      console.warn('Speech recognition not supported in this browser');
      return;
    }
    
    this.recognition = new SpeechRecognition();
    this.recognition.lang = 'en-US';
    this.recognition.continuous = false; // iOS works better with non-continuous mode
    this.recognition.interimResults = false;
    
    // Add iOS-specific error handling
    this.recognition.onerror = (event: any) => {
      console.error('Speech Recognition Error:', event.error);
      this.isListening = false;
      
      if (event.error === 'not-allowed' || event.error === 'permission-denied') {
        this.addMessage('Mentor', 
          'Microphone access was denied. Please grant permission or use text input instead.');
      } else if (event.error === 'no-speech') {
        // Don't show errors for no-speech as they're common on iOS
        console.log('No speech detected');
      }
    };
    
    // Try starting recognition
    try {
      this.recognition.start();
      this.isListening = true;
      this.userStopped = false;
      
      // Set a timeout to verify if recognition is working
      setTimeout(() => {
        if (this.isListening) {
          // If still in "listening" state after timeout, it might be stuck
          console.log('Testing if recognition is working...');
          try {
            this.recognition.stop(); // Stop and restart to verify connection
            setTimeout(() => {
              try {
                this.recognition.start();
              } catch (e) { 
                console.log('Recognition restart failed, defaulting to text input');
                this.isListening = false;
              }
            }, 300);
          } catch (e) {
            console.log('Recognition stop failed, defaulting to text input');
            this.isListening = false;
          }
        }
      }, 5000);
    } catch (error) {
      console.error('Failed to start iOS recognition:', error);
      this.isListening = false;
    }
  }
  

  initializeConversation(): void {
    this.isProcessing = true;
    const welcomeSub = this.appService.aimentorwelcome(this.userId, this.selectedRole).subscribe({
      next: (response: any) => {
        this.chatId = response.chat_id;
        this.chatService.setChatId(this.chatId);
        console.log('response:', response);
        const aiMessage = response.message.message;
        const audioUrl = response.message.audio_url;
        const imageUrl = response.message.meme_url; // Assuming your backend returns image_url
        this.addMessage('Mentor', aiMessage, audioUrl, imageUrl);
        if (audioUrl) {
          this.playAudio(audioUrl);
        }
        this.isProcessing = false;
        this.startListening();
      },
      error: (error: any) => {
        console.error('Error fetching initial greeting:', error);
        this.isProcessing = false;
      },
    });
    this.subscriptions.add(welcomeSub);
  }

  addMessage(sender: 'User' | 'Mentor', message: string, audioUrl?: string, imageUrl?: string, fileDetails?: { name: string; type: string }): void {
    // Convert markdown to HTML
    const rawHtml = marked(message);
    // Sanitize HTML to prevent XSS attacks
    const sanitizedHtml = this.sanitizer.bypassSecurityTrustHtml(rawHtml as string);
  
    this.conversation.push({
      sender,
      message,
      audioUrl,
      imageUrl,
      file: fileDetails,
      timestamp: new Date(),
      htmlContent: sanitizedHtml, // Use sanitized HTML
    });
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    setTimeout(() => {
      if (this.messagesContainer) {
        this.messagesContainer.nativeElement.scrollTop =
          this.messagesContainer.nativeElement.scrollHeight;
      }
    }, 100);
  }

  generateChatId(): string {
    return Date.now().toString();
  }

  toggleTheme(): void {
    this.isDarkMode = !this.isDarkMode;
    localStorage.setItem('theme', this.isDarkMode ? 'dark' : 'light');
  }

  initializeTheme(): void {
    const theme = localStorage.getItem('theme');
    if (theme === 'dark') {
      this.isDarkMode = true;
    }
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
    if (this.recognition) {
      this.recognition.stop();
    }
    if (this.audio) {
      this.audio.pause();
      this.audio.src = '';
    }
  }

  fetchUserProfile(): void {
    this.appService.getUserProfile().subscribe({
      next: (response) => {
        
        // Construct the full URL for the profile picture
        if (response.profile_picture) {
          this.userProfilePicture = response.profile_picture.startsWith('http') 
            ? response.profile_picture 
            : `${this.backendUrl}${response.profile_picture}`;
          console.log('User profile picture:', this.userProfilePicture);
        } else {
          this.userProfilePicture = '/assets/img/user_avtar.jpg'; // Fallback image
        }

        // Add user's interested subjects to historical figures
        if (response.user_journey && response.user_journey.interested_subjects) {
          this.addUserInterestsToFigures(response.user_journey.interested_subjects);
        }
      },
      error: (error) => {
        console.error('Error fetching user profile:', error);
        this.userProfilePicture = '/assets/img/user_avtar.jpg'; // Fallback image
      },
    });
  }

  updateFigureTranslations(): void {
    if (this.preferredLanguage !== 'en' && this.roles.length > 0) {
      // Collect all texts that need translation
      const textsToTranslate: string[] = [];
      
      // Add display names, fields and values
      this.roles.forEach(figure => {
        textsToTranslate.push(figure.display);
        textsToTranslate.push(figure.field);
        textsToTranslate.push(figure.value);
      });
      
      // Request translations
      this.appService.translateTexts(textsToTranslate, this.preferredLanguage)
        .subscribe({
          next: (response) => {
            const translations = response.translations;
            
            // Update the translated texts dictionary
            for (let i = 0; i < textsToTranslate.length; i++) {
              this.translatedTexts[textsToTranslate[i]] = translations[i];
            }
          },
          error: (err) => console.error('Error translating figure texts:', err)
        });
    }
  }

  addUserInterestsToFigures(interests: string[]): void {
    if (!interests || interests.length === 0) return;
    // Create historical figure entries from user interests
    const interestFigures: HistoricalFigure[] = interests.map(interest => ({
      display: `Expert in ${interest}`,
      value: `Expert in ${interest}`,
      field: interest
    }));
    
    // Add to the beginning of the array to show user interests first
    this.roles = [...interestFigures, ...this.roles];

    // Translate the new figures if needed
    if (this.preferredLanguage !== 'en') {
      this.updateFigureTranslations();
    }
  }
  // New method to handle file selection
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
    } else {
      this.selectedFile = null;
    }
  }

  removeSelectedFile(): void {
    this.selectedFile = null; // Reset the selected file
  }

  // New method to send text input and file
  sendTextInput(): void {
    if (this.userInputText.trim() === '' && !this.selectedFile) {
      return; // Do nothing if both fields are empty
    }

    const messageContent = this.userInputText;
    const fileDetails = this.selectedFile
    ? { name: this.selectedFile.name, type: this.selectedFile.type }
    : undefined;

    // Add user's message to the conversation
    this.addMessage('User', messageContent, undefined, undefined, fileDetails);

    // Stop any ongoing processes
    this.stopListening();
    this.isProcessing = true;

    // Call the backend service
    this.processUserInput(this.userInputText, this.selectedFile || undefined);

    // Reset input fields
    this.userInputText = '';
    this.selectedFile = null;
  }

  processUserInput(transcript: string, file?: File): void {
    this.isProcessing = true;
    const chatSub = this.appService
      .aimentorchat(this.userId, this.chatId, this.turnId, transcript, file)
      .subscribe({
        next: (response: any) => {
          const aiMessage = response.message;
          const audioUrl = response.audio_url;
          const imageUrl = response.meme_url;

          this.addMessage('Mentor', aiMessage, audioUrl, imageUrl);
          if (audioUrl) {
            this.playAudio(audioUrl);
          }
          console.log('response:', response);
          this.turnId += 1;
          this.isProcessing = false;
        },
        error: (error: any) => {
          console.error('Error processing user input:', error);
          this.isProcessing = false;
          this.startListening();
        },
      });
    this.subscriptions.add(chatSub);
  }


  updateSelectedRoleImage(event: any): void {
    const selectedFigure = this.roles.find(figure => figure.value === event.value);
    this.selectedRoleImageUrl = selectedFigure?.imageUrl || 'assets/img/banner.png';
  }
  
}
