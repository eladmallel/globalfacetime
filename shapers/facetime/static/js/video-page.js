// Initialize API key, session, and token...
// Think of a session as a room, and a token as the key to get in to the room
// Sessions and tokens are generated on your server and passed down to the client
var apiKey = "41805792";

var SERVICE_ID = 'chatsummit2';

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

    this.disconnectCb = disconnectCb;
    this.connectCb = connectCb;
    this.readyCb = readyCb;
    this.inSession = false;

    // Connect to XirSys
    console.log("Connecting to XirSys...");

    this.peerConnectionConfig = null;
    this.webrtc = null;
    var self=this;
    $.ajax({
        type: "POST",
        dataType: "json",
        url: "https://api.xirsys.com/getIceServers",
        data: {
            ident: "hochbergg",
            secret: "20313345-b51a-4a06-96dd-6f4d126c1848",
            domain: "chatsummit.herokuapp.com",
            application: "default",
            room: 'default',
            secure: 1
        },
        success: function (data, status) {
            // data.d is where the iceServers object lives
            self.peerConnectionConfig = data.d;

            self._initializeWebRTC();
        },
        async: false
    });
  }

  ChatClient.prototype._initializeWebRTC = function() {
    this.webrtc = new SimpleWebRTC({
        //url: 'http://summitsignal.herokuapp.com:80',
        //url: 'http://10.0.0.13:8888',
        url: 'http://174.129.2.170:8888',
        // the id/element dom element that will hold "our" video
        localVideoEl: this.$localContainer[0],
        // the id/element dom element that will hold remote videos
//        remoteVideosEl: this.$remoteContainer[0],
        // immediately ask for camera access
        autoRequestMedia: true,
        // Give peerConnectionConfig
        peerConnectionConfig: this.peerConnectionConfig
    });

    var self=this;
    this.webrtc.on('videoAdded', function(video) {
        self._onVideoAdded(video);
    });

    this.webrtc.on('videoRemoved', function() {
        self._onVideoRemoved();
    })

    // we have to wait until it's ready
    this.webrtc.on('readyToCall', function () {
        self._unpauseAndResize();
        self.readyCb();
    });
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

  ChatClient.prototype._onVideoAdded = function(video) {
    console.log("videoAdded");

    if(!this.inSession) {
        this.inSession = true;
        this._registerVideoResize(video);
        this.$remoteContainer.append(video);
        this._unpauseAndResize();

        this.connectCb();
    }
  }

  ChatClient.prototype._onVideoRemoved = function() {
      console.log("videoRemoved");
      this._disconnect();
  }

  ChatClient.prototype.listen = function(newSessionId,newLocalContainer,newRemoteContainer) {
    console.log('listen called');

    // Not much else to do, its all event
    this.sessionId = newSessionId;
    console.log("Joining room because of listen", newSessionId);
    this.webrtc.joinRoom(''+newSessionId);
    console.log("Joined room because of listen", newSessionId);
    this._switchContainers(newLocalContainer,newRemoteContainer);
    this.connected = true;
  }

  ChatClient.prototype.connect = function(newSessionId, newLocalContainer, newRemoteContainer) {
    console.log('connect called');

    // And now for the new session
    this.sessionId = newSessionId;
    console.log("Joining room because of connect", newSessionId);
    this.webrtc.joinRoom(''+newSessionId);
    console.log("Joined room because of connect", newSessionId);
    this._switchContainers(newLocalContainer,newRemoteContainer);

    console.log('Connecting to session',this.sessionId);
    this.connected = true;
  }

  ChatClient.prototype.disconnect = function() {
    console.log("disconnect called");

    this._disconnect();
    // No need to empty local, as we keep it around
    // this.$remoteContainer.empty();
    // this.disconnectCb();
  }

  ChatClient.prototype._disconnect = function() {
      if ( this.connected ) {
        this.connected = false;
        this.inSession = false;
        this.$remoteContainer.empty();
        this.webrtc.leaveRoom();
        this.disconnectCb();
      }
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
          self.chatClient.listen(self.sessionId,self.$publisherContainer,self.$subscriberContainer);
        } else {
          console.log("connecting");
          self.chatClient.connect(self.sessionId,self.$publisherContainer,self.$subscriberContainer);
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

        this.partner = profile;
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
            if ( self.inSession ) {
                self._processHeartbeats(data.now, data.heartbeats, self.sessionId);
                self._processProfiles(self.user, data.profiles);
            }
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

function ConnectButtonHandler($button) {
  var self = this;

  $button.on('click', function () {
    $.gritter.add({title: "Connecting...", text: "This might take a few seconds."});

    window.analytics.track("Connect Clicked", {
        'connectTo': window.chatWindow.partner.email
    });

    $.ajax({
        method: "GET",
        dataType: "JSON",
        url: "/sharecontact",
        data: {
          sessionId:window.chatWindow.sessionId,
          user:window.chatWindow.user
        },
        success: function(data) {
          if (data.successful) {
            $.gritter.add({title: "Connected!", text: "Your email address was sent to your peer for follow up!"});
          } else {
            $.gritter.add({title: "Oops!", text: "ChatSummit couldn't email your peer... Exchange emails verbally while you still can!"});            
          }         
        },
        error: function(error) {
          $.gritter.add({title: "Oops!", text: "ChatSummit couldn't email your peer... Exchange emails verbally while you still can!"});
        }
      });
  });
}
