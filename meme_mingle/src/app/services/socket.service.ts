import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../shared/environments/environment';
import * as io from 'socket.io-client';

@Injectable({
  providedIn: 'root'
})
export class SocketService {
  private socket: any;

  constructor() {
    this.socket = io.connect(environment.baseUrl);
    
    // Add error logging
    this.socket.on('connect_error', (error: any) => {
      console.error('Socket connection error:', error);
    });
    
    this.socket.on('error', (error: any) => {
      console.error('Socket error:', error);
    });
  }

  connect() {
    this.socket = io.connect(environment.baseUrl);
  }

  // Updated method to toggle post likes with userId
  likePost(postId: string, userId: string, isLiking: boolean) {
    this.socket.emit('toggle_like_post', { 
      post_id: postId,
      user_id: userId,
      is_liking: isLiking
    });
  }

  // Method to emit comment_post event
  commentPost(postId: string, comment: string, userId: string = 'Anonymous') {
    this.socket.emit('comment_post', { 
      post_id: postId, 
      comment: comment,
      user_id: userId
    });
  }

  // Listen for post_liked events
  onPostLiked(): Observable<any> {
    return new Observable(observer => {
      this.socket.on('post_liked', (data: any) => {
        observer.next(data);
      });
    });
  }
  
  // Listen for post_unliked events
  onPostUnliked(): Observable<any> {
    return new Observable(observer => {
      this.socket.on('post_unliked', (data: any) => {
        observer.next(data);
      });
    });
  }

  // Listen for post_commented events
  onPostCommented(): Observable<any> {
    return new Observable(observer => {
      this.socket.on('post_commented', (data: any) => {
        observer.next(data);
      });
    });
  }

  // Listen for error events
  onError(): Observable<any> {
    return new Observable(observer => {
      this.socket.on('error', (data: any) => {
        observer.next(data);
      });
    });
  }

  // Method to join a specific group room
  joinGroupRoom(groupId: string, userId: string) {
    this.socket.emit('join_group_room', { group_id: groupId, user_id: userId });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
}