// Initialize API key, session, and token...
// Think of a session as a room, and a token as the key to get in to the room
// Sessions and tokens are generated on your server and passed down to the client
var apiKey = "41805792";

GlobalFaceTime = {}
GlobalFaceTime.user = "" + Math.floor(Math.random()*100000);

SUBSCRIBER_DIV_NAME_BASE = "subscriberDiv";
PUBLISHER_DIV_NAME_BASE = "publisherDiv";

MAXIMUM_HEARTBEAT_AGE_BEFORE_DISCONNECT_MILLI = 20000;

TEMPORARY_PUBLISHER_CONTAINER_ID = "temporaryPublisherContainer";

ChatPublisher = (function() {
  var session;
  var publisher;
  var $defaultPublisherContainer;
  var $currentPublisherContainer;
  var publisherId;

  function ChatPublisher(thePublisherId) {
    publisherId = thePublisherId;
    // Create a default publisher container
    $defaultPublisherContainer = $(document.createElement("div"));
    $defaultPublisherContainer.attr("id",TEMPORARY_PUBLISHER_CONTAINER_ID);
    $defaultPublisherContainer.css("display","none");
    $defaultPublisherContainer.appendTo($("body"));

    // And set it as the current container
    $currentPublisherContainer = $defaultPublisherContainer;

    // Create an element to be replaced by the publisher
    var publisherElement = document.createElement("div");
    publisherElement.setAttribute("id",publisherId);
    $currentPublisherContainer[0].appendChild(publisherElement);

    // Start publishing
    var publisherProperties = {
      rememberDeviceAccess: true,
    };

    publisher = TB.initPublisher(apiKey, publisherId, publisherProperties);
  }

  ChatPublisher.prototype._switchContainer = function(newContainer) {
    console.log("CP: Switching container to "+newContainer);
    var $newPublisherContainer = $(newContainer);
    $currentPublisherContainer.children().appendTo($newPublisherContainer);
    $currentPublisherContainer = $newPublisherContainer;

    this._unpauseAndResize();
  }

  ChatPublisher.prototype._unpauseAndResize = function() {
    console.log("CP: Unpause and Resize");

    // Unpause the video
    var videos = $currentPublisherContainer.find("video");
    for (var i = 0; i < videos.length; i++) {
      videos[i].play();
    }

    // Resize my publisher to fit
    var $publisherElement = $(document.getElementById(publisher.id));
    $publisherElement.width($currentPublisherContainer.width());                         
    $publisherElement.height($currentPublisherContainer.height());
  }

  ChatPublisher.prototype.publishTo = function(newSession,newContainer) {
    console.log("CP: Publishing - new container is "+newContainer);
    // Keep my event listener on the old session, if we had one - so when *it* closes, it doesn't close my publisher

    // And now for the new session
    session = newSession;

    function sessionDisconnectedHandler(event) {
      event.preventDefault(); // So it won't destroy my publisher
      this._switchContainer($defaultPublisherContainer); // Switch to the default container
    }

    function streamCreatedHandler(event) {
      console.log("CP: stream created");
      this._unpauseAndResize();
    }

    function streamPropertyChangedHandler(event) {
      console.log("CP: stream property changed");
      this._unpauseAndResize();
    }

    // To make sure my publisher won't get destroyed
    session.addEventListener('sessionDisconnected', sessionDisconnectedHandler,this);

    // To resize my publisher when it gets published
    session.addEventListener('streamCreated', streamCreatedHandler,this);
    session.addEventListener('streamPropertyChanged', streamPropertyChangedHandler,this);

    // Finally - publish
    session.publish(publisher);

    // And put our publisher in the container
    this._switchContainer(newContainer);
  }

  return ChatPublisher;
})();

ChatWindow = (function() {
  // To track unique div names
  ChatWindow.chatWindowCount = 0;

  var sessionId;
  var session;
  var user;
  var self;
  var $publisherContainer;  
  var $subscriberContainer;
  var $parentContainer;
  var chatWindowNumber;
  var subscriberDivId;
  var publisherDivId;
  var closedCallback;
  var chatPublisherObj;

  function ChatWindow(myUser,chatPublisher,publisherContainer,subscriberContainer,parentContainer,onClosedCallback) {
    this.user = myUser;
    self = this;

    $publisherContainer = $(publisherContainer);
    $subscriberContainer = $(subscriberContainer);
    $parentContainer = $(parentContainer);
    chatPublisherObj = chatPublisher;

    // Create a unique identifier
    chatWindowNumber = ChatWindow.chatWindowCount;
    ChatWindow.chatWindowCount++;

    closedCallback = onClosedCallback;

    // We aren't connected yet, so we can't be searching for a partner
    console.log("Connecting: Not looking for partner");
    $parentContainer.removeClass("searching-for-partner");
  }

  ChatWindow.prototype.connect = function() {
    $.ajax({
      method: "GET",
      url: "/connect",
      dataType: "json",
      data: {"user":self.user},
      success: function(data) {
          console.log("Got data from server: ");
          console.log(data);

          session = TB.initSession(data.sessionId);
          sessionId = data.sessionId;

          console.log("session");
          console.log(session);

          function connectToStreams(streams) {
              for (var i = 0; i < streams.length; i++) {
                  var stream = streams[i];
                  if (stream.connection.connectionId != session.connection.connectionId) {

                    // Create an element to be replaced by the flash
                    subscriberDivId = SUBSCRIBER_DIV_NAME_BASE+"_"+chatWindowNumber;
                    var subscriberElement = document.createElement("div");
                    subscriberElement.setAttribute("id",subscriberDivId);
                    $subscriberContainer[0].appendChild(subscriberElement);

                    // RTC size change
                    var subscriberProperties = {
                      width: $subscriberContainer.width(),
                      height: $subscriberContainer.height()
                    };

                    // Subscribe to the remote stream
                    var subscriber = session.subscribe(stream, subscriberDivId, subscriberProperties); 

                    // We're no longer looking for a partner (for UI purposes)
                    console.log("Found partner: Not looking for partner");
                    $parentContainer.removeClass("searching-for-partner");

                    // Flash size change
                    var subscriberFlashElement = document.getElementById(subscriber.id);
                    subscriberFlashElement.width = $subscriberContainer.width();                         
                    subscriberFlashElement.height = $subscriberContainer.height();
                  }
              }
          }

          function sessionConnectedHandler(event) {
              console.log("in sessionConnectedHandler");

              // Publish
              chatPublisherObj.publishTo(session,$publisherContainer);
              console.log("published");

              // Now we wait for a partner - mark our subscriber div as waiting for partner (for UI purposes)
              console.log("Connected: Looking for partner");
              $parentContainer.addClass("searching-for-partner");

              connectToStreams(event.streams);
          }

          function streamCreatedHandler(event) {
              connectToStreams(event.streams);
          }

          function streamDestroyedHandler(event) {
               console.log("streamDestroyedHandler");
               console.log(event);
               self.disconnect();
          }

          function sessionDisconnectedHandler(event) {
               console.log("sessionDisconnectedHandler");
               console.log(event);
               self._disconnectCleanup(); // no need to call disconnect() again
          }

          function connectionDestroyedHandler(event) {
               console.log("sessionDestroyedHandler");
               console.log(event);
               self.disconnect();
          }

          session.addEventListener('sessionConnected', sessionConnectedHandler);
          session.addEventListener('streamCreated', streamCreatedHandler);

          session.addEventListener('streamDestroyed', streamDestroyedHandler);
          session.addEventListener('sessionDisconnected', sessionDisconnectedHandler);
          session.addEventListener('connectionDestroyed', connectionDestroyedHandler);

          session.connect(apiKey, data.token);

          console.log("connecting");                  
      },
      error: function(error) {

      } 
    });

    function processHeartbeats(now,heartbeats) {
         var nowDate = new Date(now);

         //console.log("HEARTBEAT: Processing ");
         //console.log(heartbeats);

         for (var currUser in heartbeats) {
              var lastHeartbeat = new Date(heartbeats[currUser]);

              var staleness = nowDate - lastHeartbeat;
              //console.log("HEARTBEAT: Staleness of " + currUser + " is " + staleness);

              if (staleness >= MAXIMUM_HEARTBEAT_AGE_BEFORE_DISCONNECT_MILLI) {
                   console.log("Chat is stale ("+staleness+"). Disconnect.");
                   self.disconnect();
              }
         }
    }

    (function(){
         if (typeof sessionId != 'undefined') {
              $.ajax({
                   method: "GET",
                   dataType: "JSON",
                   url: "/heartbeat",
                   data: {
                        sessionId:sessionId,
                        user:self.user
                   },
                   success: function(data) {
                        processHeartbeats(data.now,data.heartbeats);
                   }
              });
         }

        setTimeout(arguments.callee, 1000);
    })();
  }

  ChatWindow.prototype._disconnectCleanup = function() {
    if (typeof session != "undefined") {
        console.log("Disconnecting from chat...");
        session = undefined;
        sessionId = undefined;

        if ( typeof closedCallback != "undefined") {
          closedCallback(self);
        }
   }
  }
  ChatWindow.prototype.disconnect = function() {
         if (typeof session != "undefined") {
              session.disconnect();
         }
    }

  return ChatWindow;
})();
          