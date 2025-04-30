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
  sourceLanguage?: string;
  targetLanguage?: string;
  isInterim?: boolean;
}

export interface FullTranslationResult {
  originalText: string;
  translatedText: string;
}

@Injectable({
  providedIn: 'root'
})
export class SpeechTranslationService {
  private hubConnection: signalR.HubConnection | null = null;
  private translationResultSubject = new BehaviorSubject<TranslationResult | null>(null);
  translationResult$ = this.translationResultSubject.asObservable();

  private interimTranslationSubject = new BehaviorSubject<TranslationResult | null>(null);
  interimTranslation$ = this.interimTranslationSubject.asObservable();

  private fullTranslationResultSubject = new BehaviorSubject<FullTranslationResult | null>(null);
  fullTranslationResult$ = this.fullTranslationResultSubject.asObservable();

  private connectionStatusSubject = new BehaviorSubject<string>('disconnected');
  connectionStatus$ = this.connectionStatusSubject.asObservable();

  private isListeningSubject = new BehaviorSubject<boolean>(false);
  isListening$ = this.isListeningSubject.asObservable();

  constructor(private http: HttpClient) { }

  public async initializeConnection(): Promise<void> {
    if (this.hubConnection) {
      return;
    }

    this.hubConnection = new signalR.HubConnectionBuilder()
      .withUrl(`${environment.apiBaseUrl}/translationHub`)
      .withAutomaticReconnect()
      .build();

    this.hubConnection.on('ReceiveTranslation', 
      (originalText: string, translatedText: string, sourceLanguage?: string, targetLanguage?: string) => {
        this.translationResultSubject.next({
          originalText,
          translatedText,
          sourceLanguage,
          targetLanguage,
          isInterim: false
        });
      }
    );

    this.hubConnection.on('ReceiveInterimTranslation', 
      (originalText: string, translatedText: string, sourceLanguage?: string, targetLanguage?: string) => {
        this.interimTranslationSubject.next({
          originalText,
          translatedText,
          sourceLanguage,
          targetLanguage,
          isInterim: true
        });
      }
    );

    this.hubConnection.on('ReceiveFullTranslation', 
      (originalText: string, translatedText: string) => {
        this.fullTranslationResultSubject.next({
          originalText,
          translatedText
        });
      }
    );

    this.hubConnection.on('TranslationStarted', () => {
      console.log('Translation started');
      this.isListeningSubject.next(true);
    });

    this.hubConnection.on('TranslationEnded', () => {
      console.log('Translation ended');
      this.isListeningSubject.next(false);
    });

    this.hubConnection.on('TranslationError', (errorMessage: string) => {
      console.error('Translation error:', errorMessage);
      this.isListeningSubject.next(false);
    });

    this.hubConnection.onreconnecting(() => {
      this.connectionStatusSubject.next('reconnecting');
    });

    this.hubConnection.onreconnected(() => {
      this.connectionStatusSubject.next('connected');
    });

    this.hubConnection.onclose(() => {
      this.connectionStatusSubject.next('disconnected');
    });

    try {
      await this.hubConnection.start();
      console.log('SignalR connection established');
      this.connectionStatusSubject.next('connected');
    } catch (err) {
      console.error('Error starting SignalR connection', err);
      this.connectionStatusSubject.next('error');
      throw err;
    }
  }

  public startTranslation(request: TranslationRequest): Observable<any> {
    return this.http.post(`${environment.apiBaseUrl}/api/speech/start`, request);
  }

  public stopTranslation(): Observable<any> {
    return this.http.post(`${environment.apiBaseUrl}/api/speech/stop`, {});
  }

  public resetFullTranslation(): void {
    this.fullTranslationResultSubject.next(null);
  }

  public disconnectSignalR(): void {
    if (this.hubConnection) {
      this.hubConnection.stop()
        .then(() => {
          console.log('SignalR connection stopped');
          this.connectionStatusSubject.next('disconnected');
        })
        .catch((err: Error) => console.error('Error stopping SignalR connection:', err));
      this.hubConnection = null;
    }
  }
}
