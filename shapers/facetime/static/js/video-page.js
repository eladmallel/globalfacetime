// Initialize API key, session, and token...
// Think of a session as a room, and a token as the key to get in to the room
// Sessions and tokens are generated on your server and passed down to the client
var apiKey = "41805792";

var SERVICE_ID = 'chatsummit';

GlobalFaceTime = {}
GlobalFaceTime.user = "" + profile_id;

SUBSCRIBER_DIV_NAME_BASE = "subscriberDiv";
PUBLISHER_DIV_NAME_BASE = "publisherDiv";

MAXIMUM_HEARTBEAT_AGE_BEFORE_DISCONNECT_MILLI = 20000;

TEMPORARY_LOCAL_CONTAINER_ID = "temporary-local-container";
TEMPORARY_REMOTE_CONTAINER_ID = "temporary-remote-container";
LOCAL_STREAM_ID = 'local-stream';
REMOTE_STREAM_ID = 'remote-stream';

ChatClient = (function() {
  function ChatClient(authKey,readyCb,connectCb,disconnectCb) {
    this.connected = false;

    // Create a default publisher container
    this.$localContainer = $("<div style='display: none;' id='"+TEMPORARY_LOCAL_CONTAINER_ID+"'></div>").appendTo($("body"));
    this.$remoteContainer = $("<div style='display: none;' id='"+TEMPORARY_REMOTE_CONTAINER_ID+"'></div>").appendTo($("body"));

    this.authKey = authKey;
    this.disconnectCb = disconnectCb;
    this.connectCb = connectCb;

    this.client = vline.Client.create({
      serviceId: window.SERVICE_ID
    });

    // Handle a new incoming connection
    this.client.on('add:mediaSession', function(event) { this._onMediaSession(event.target); }, this);

    // Show the local stream
    this.client.getLocalStream().done(function(mediaStream) {
      console.log("GOT LOCAL STREAM");

      if (mediaStream === this.localStream) {
        return;
      }

      if (typeof(this.localStream) !== 'undefined') {
        console.log("GOT DOUBLE LOCAL STREAM!");

        this.localStream.stop();
        this.$localContainer.empty();
      }

      this.localStream = mediaStream;
      this.localStreamElement = mediaStream.createVideoElement();
      this.localStreamElement.id = LOCAL_STREAM_ID;
      this._registerVideoResize(this.localStreamElement);
      this.$localContainer.append(this.localStreamElement);

      this._unpauseAndResize();
    },this);

    // Connect to vline
    console.log("Connecting to vline...");
    this.client.login(window.SERVICE_ID, {}, this.authKey).done(function(session) {
      this.vlineSession = session;

      readyCb();
    }, this);
  }

  ChatClient.prototype._switchContainers = function(newLocalContainer,newRemoteContainer) {
    //console.log("CP: Switching containers to "+newLocalContainer+", "+newRemoteContainer);
    
    this.$localContainer.children().appendTo($(newLocalContainer));
    this.$localContainer = $(newLocalContainer);

    this.$remoteContainer.children().appendTo($(newRemoteContainer));
    this.$remoteContainer = $(newRemoteContainer);
    
    this._unpauseAndResize();
  }

  ChatClient.prototype._registerVideoResize = function(element) {
    var $el = $(element);

    var self=this;
    $el.on('loadedmetadata', function() {
      self._unpauseAndResize();
    });
  }

  ChatClient.prototype._unpauseAndResize = function() {
    //console.log("CP: Unpause and Resize");

    function doContainer($cont) {
      // Unpause the video
      var videos = $cont.find("video");
      for (var i = 0; i < videos.length; i++) {
        var video = videos[i];
        video.play();

        var $video = $(video);
        var contAspect = $cont.width() / $cont.height();
        var videoAspect = $video.width() / $video.height();

        if (contAspect > videoAspect) {
          var scaleFactor = $video.width() / $cont.width()
          var endHeight = $video.height() / scaleFactor;

          $video.css({
            width: $cont.width(),
            position: 'relative',
            height: '',
            top: -((endHeight - $cont.height()) / 2),
            left: 0
          });
        } else {
          var scaleFactor = $video.height() / $cont.height()
          var endWidth = $video.width() / scaleFactor;

          $video.css({
            height: $cont.height(),
            position: 'relative',
            width: '',
            left: -((endWidth - $cont.width()) / 2),
            top: 0
          });
        }
      }
    }

    doContainer(this.$localContainer);
    doContainer(this.$remoteContainer);
  }

  ChatClient.prototype._onMediaSession = function(mediaSession) {
    if (mediaSession === this.mediaSession) {
      return;
    }

    console.log("Got a media session! No longer searching for a partner :)");
    this.connectCb();

    if ( typeof(this.mediaSession) !== 'undefined') {
      this.mediaSession.stop();
    }

    this.mediaSession = mediaSession;

    var mySessionId = this.sessionId; // To prevent from old events interfering with us

    mediaSession.
    on('enterState:pending', function() {
      //console.log('Sessions ' + this.sessionId + ' entering pending state...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    },this).
    on('exitState:pending', function() {
      //console.log('Session ' + this.sessionId + ' exiting pending state...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    },this).
    on('enterState:incoming', function() {
      //console.log('Session ' + this.sessionId + ' entering incoming state...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    },this).
    on('exitState:incoming', function() {
      //console.log('Session ' + this.sessionId + ' exiting incoming state...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    },this).
    on('enterState:outgoing', function() {
      //console.log('Session ' + this.sessionId + ' entering outgoing state...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    },this).
    on('exitState:outgoing', function() {
      //console.log('Session ' + this.sessionId + ' exiting outgoing state...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    },this).
    on('enterState:connecting', function() {
      //console.log('Session ' + this.sessionId + ' entering connecting state...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    },this).
    on('exitState:connecting', function() {
      //console.log('Session ' + this.sessionId + ' exiting connecting state...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    },this).
    on('enterState:active', function() {
      //console.log('Session ' + this.sessionId + ' entering active state...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    },this).
    on('exitState:active', function() {
      //console.log('Session ' + this.sessionId + ' exiting active state...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    },this).
    on('mediaSession:removeRemoteStream', function(event) {
      //console.log('Session ' + this.sessionId + ' lost a remote stream...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    }, this).
    on('mediaSession:removeLocalStream', function(event) {
      //console.log('Session ' + this.sessionId + ' lost a local stream...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    }, this).
    on('change:mediaState', function(event) {
      console.log('Session ' + this.sessionId + ' media state changed from '+event.oldVal + ' to ' + event.val);
      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }

      if ( event.val === 'closed' || event.val === 'disconnected' || event.val === 'inactive') {
        this.disconnect();
      }
    }, this).
    on('mediaSession:addLocalStream', function(event) {
      //console.log('Session ' + this.sessionId + ' got a local stream...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }
    }, this).
    on('mediaSession:addRemoteStream', function(event) {
      var remoteStream = event.stream;

      if (remoteStream === this.remoteStream) {
        return;
      }

      console.log("GOT REMOTE STREAM");
      //console.log('Session ' + this.sessionId + ' got a remote stream...');

      if (this.sessionId !== mySessionId) {
        console.log("GOT STALE EVENT....");
        return;
      }

      if (typeof(this.remoteStream) !== 'undefined') {
        console.log("GOT DOUBLE REMOTE STREAM!");

        //this.remoteStream.stop();
        this.$remoteContainer.empty();
      }
      
      this.remoteStream = remoteStream;
      this.remoteStreamElement = remoteStream.createVideoElement();
      this.remoteStreamElement.id = REMOTE_STREAM_ID;
      this._registerVideoResize(this.remoteStreamElement);
      this.$remoteContainer.append(this.remoteStreamElement);

      this._unpauseAndResize();
    }, this);

    if ( mediaSession.isIncoming()) {
      // Accept the call if its incoming
      mediaSession.start();
    }
  }

  ChatClient.prototype.listen = function(newSessionId,newLocalContainer,newRemoteContainer) {
    //console.log("CP: Listening on " + newSessionId + " - New local container is " + newLocalContainer + " New remote is " + newRemoteContainer);

    // Not much else to do, its all event
    this.sessionId = newSessionId;
    this._switchContainers(newLocalContainer,newRemoteContainer);
    this.connected = true;
  }
  ChatClient.prototype.connect = function(newSessionId,newLocalContainer,newRemoteContainer) {
    //console.log("CP: Connecting to " + newSessionId + " - New local container is " + newLocalContainer + " New remote is " + newRemoteContainer);

    // And now for the new session
    this.sessionId = newSessionId;
    this._switchContainers(newLocalContainer,newRemoteContainer);
    console.log('Connecting to session',this.sessionId);
    this.session = this.vlineSession.startMedia(newSessionId);
    
    this.connected = true;
  }

  ChatClient.prototype.disconnect = function() {
    if ( this.connected === false) {
      return;
    }

    console.log("DISCONNECTING!!!!");

    this.connected = false;

    if (typeof(this.mediaSession) !== 'undefined') {
      if (!this.mediaSession.isClosed()) {
        this.mediaSession.stop();
      }
      this.mediaSession = undefined;
    }

    // No need to empty local, as we keep it around
    this.$remoteContainer.empty();

    this.disconnectCb();
  }

  return ChatClient;
})();

ChatWindow = (function() {
  function ChatWindow(user,chatClient,publisherContainer,subscriberContainer) {
    this.$publisherContainer = $(publisherContainer);
    this.$subscriberContainer = $(subscriberContainer);
    this.chatClient = chatClient;

    this.connected = false;
    this.inSession = false;
    this.user = user;

    this._sendHeartbeat(); // Start the heartbeats
  }

  ChatWindow.prototype.connect = function() {
    if (this.connected) {
      throw Exception("Cannot connect using an already connected ChatWindow");
    }

    this.connected = true;

    var self=this;
    $.ajax({
      method: "GET",
      url: "/connect",
      dataType: "json",
      data: {
        "profile_id":self.user
      },
      success: function(data) {
        console.log("Got data from server: ");
        console.log(data);

        self.inSession = true;
        self.sessionId = data.sessionId;
        self.peerId = data.peerId;
        self.peerProfile = data.peerProfile;

        // Get a partner
        //console.log("Got Session: Now get a partner");
        if (self.peerId === self.user) {
          console.log("listening");
          self.chatClient.listen(self.peerId,self.$publisherContainer,self.$subscriberContainer);  
        } else {
          console.log("connecting");
          self.chatClient.connect(self.peerId,self.$publisherContainer,self.$subscriberContainer);
          window.peerEmail = self.peerProfile.email
        }
      },
    });
  }

  ChatWindow.prototype._processHeartbeats = function(now, heartbeats, sessionId) {
    var nowDate = new Date(now);

    //console.log("HEARTBEAT: Processing ");
    //console.log(heartbeats);

    for (var currUser in heartbeats) {
      var lastHeartbeat = new Date(heartbeats[currUser]);

      var staleness = nowDate - lastHeartbeat;
    
      //console.log("HEARTBEAT FOR "+sessionId);
      //console.log("HEARTBEAT: Staleness of " + currUser + " is " + staleness);

      if (staleness >= MAXIMUM_HEARTBEAT_AGE_BEFORE_DISCONNECT_MILLI) {
        console.log("Chat is stale ("+staleness+"). Disconnect.");
        this.disconnect();
      }
    }    
  }

  ChatWindow.prototype._processProfiles = function(my_profile_id, profiles) {
    for (var profile_id in profiles) {
      if (profile_id != my_profile_id) {
        var profile = profiles[profile_id];
        $('.partner-name').text(profile.name);
        $('.partner-description').text(profile.interests);
        $('.partner-profile-picture').removeClass('default');
        $('.partner-profile-picture').css('background-image', 'url(' + profile.avatar + ')');
      }
    }
  }

  ChatWindow.prototype._sendHeartbeat = function() {
    //console.log("SENDING HEARTBEAT? "+this.inSession);

    var self = this;

    if ( this.inSession ) {
      $.ajax({
        method: "GET",
        dataType: "JSON",
        url: "/heartbeat",
        data: {
          sessionId:this.sessionId,
          user:this.user
        },
        success: function(data) {
          self._processHeartbeats(data.now, data.heartbeats, self.sessionId);
          self._processProfiles(self.user, data.profiles);
        }
      });
    }

    var self = this;
    var f = arguments.callee;

    setTimeout(function() {
      f.call(self);
    }, 1000);
  }

  ChatWindow.prototype.disconnect = function() {
    if (this.connected === false) {
      return;
    }
    this.connected = false;
    this.inSession = false;

    this.chatClient.disconnect();
  }

  return ChatWindow;
})();
