import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import * as signalR from '@microsoft/signalr';
import { environment } from '../shared/environments/environment';

export interface TranslationRequest {
  sourceLanguage: string;
  targetLanguage: string;
}

export interface TranslationResult {
  originalText: string;
  translatedText: string;
  sourceLanguage: string;
  targetLanguage: string;
}

export interface FullTranslationResult {
  originalText: string;
  translatedText: string;
}

@Injectable({
  providedIn: 'root'
})
export class SpeechTranslationService {
  private hubConnection?: signalR.HubConnection;
  private translationResult = new BehaviorSubject<TranslationResult | null>(null);
  private fullTranslationResult = new BehaviorSubject<FullTranslationResult | null>(null);
  private connectionStatus = new BehaviorSubject<string>('disconnected');
  private isListening = new BehaviorSubject<boolean>(false);

  constructor(private http: HttpClient) { }

  public get translationResult$(): Observable<TranslationResult | null> {
    return this.translationResult.asObservable();
  }

  public get fullTranslationResult$(): Observable<FullTranslationResult | null> {
    return this.fullTranslationResult.asObservable();
  }

  public get connectionStatus$(): Observable<string> {
    return this.connectionStatus.asObservable();
  }

  public get isListening$(): Observable<boolean> {
    return this.isListening.asObservable();
  }

  public initializeConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.hubConnection = new signalR.HubConnectionBuilder()
        .withUrl(`${environment.apiBaseUrl}/translationHub`)
        .withAutomaticReconnect()
        .build();

      this.hubConnection.start()
        .then(() => {
          console.log('SignalR connection established');
          this.connectionStatus.next('connected');
          this.setupSignalRListeners();
          resolve();
        })
        .catch((err: Error) => {
          console.error('Error establishing SignalR connection:', err);
          this.connectionStatus.next('error');
          reject(err);
        });
    });
  }

  private setupSignalRListeners(): void {
    if (!this.hubConnection) return;

    this.hubConnection.on('ReceiveTranslation', 
      (originalText: string, translatedText: string, sourceLanguage: string, targetLanguage: string) => {
        this.translationResult.next({
          originalText,
          translatedText,
          sourceLanguage,
          targetLanguage
        });
      }
    );

    this.hubConnection.on('ReceiveFullTranslation', 
      (originalText: string, translatedText: string) => {
        this.fullTranslationResult.next({
          originalText,
          translatedText
        });
      }
    );

    this.hubConnection.on('TranslationStarted', () => {
      console.log('Translation started');
      this.isListening.next(true);
    });

    this.hubConnection.on('TranslationEnded', () => {
      console.log('Translation ended');
      this.isListening.next(false);
    });

    this.hubConnection.on('TranslationError', (errorMessage: string) => {
      console.error('Translation error:', errorMessage);
      this.isListening.next(false);
    });
  }

  public startTranslation(request: TranslationRequest): Observable<any> {
    return this.http.post(`${environment.apiBaseUrl}/api/speech/start`, request);
  }

  public stopTranslation(): Observable<any> {
    return this.http.post(`${environment.apiBaseUrl}/api/speech/stop`, {});
  }

  public resetFullTranslation(): void {
    this.fullTranslationResult.next(null);
  }

  public disconnectSignalR(): void {
    if (this.hubConnection) {
      this.hubConnection.stop()
        .then(() => {
          console.log('SignalR connection stopped');
          this.connectionStatus.next('disconnected');
        })
        .catch((err: Error) => console.error('Error stopping SignalR connection:', err));
    }
  }
}
