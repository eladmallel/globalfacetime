// Initialize API key, session, and token...
// Think of a session as a room, and a token as the key to get in to the room
// Sessions and tokens are generated on your server and passed down to the client
var apiKey = "41805792";

GlobalFaceTime = {}
GlobalFaceTime.user = "" + Math.floor(Math.random()*100000);

SUBSCRIBER_DIV_NAME_BASE = "subscriberDiv";
PUBLISHER_DIV_NAME_BASE = "publisherDiv";

MAXIMUM_HEARTBEAT_AGE_BEFORE_DISCONNECT_MILLI = 10000;

ChatWindow = (function() {
  // To track unique div names
  ChatWindow.chatWindowCount = 0;

  var sessionId;
  var session;
  var user;
  var self;
  var $publisherContainer;
  var $subscriberContainer;
  var chatWindowNumber;
  var subscriberDivId;
  var publisherDivId;

  function ChatWindow(myUser,publisherContainer,subscriberContainer) {
    this.user = myUser;
    self = this;

    $publisherContainer = $(publisherContainer);
    $subscriberContainer = $(subscriberContainer);

    // Create a unique identifier
    chatWindowNumber = ChatWindow.chatWindowCount;
    ChatWindow.chatWindowCount++;
  }

  ChatWindow.prototype.connect = function() {
    $.ajax({
      method: "GET",
      url: "/connect",
      dataType: "json",
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

                    // Subscribe to the remote stream
                    var subscriber = session.subscribe(stream, subscriberDivId); 
                    var subscriberFlashElement = document.getElementById(subscriber.id);

                    subscriberFlashElement.width = $subscriberContainer.width();                         
                    subscriberFlashElement.height = $subscriberContainer.height();
                  }
              }
          }

          function sessionConnectedHandler(event) {
              console.log("in sessionConnectedHandler");

              // Create an element to be replaced by the flash
              publisherDivId = PUBLISHER_DIV_NAME_BASE+"_"+chatWindowNumber;
              var publisherElement = document.createElement("div");
              publisherElement.setAttribute("id",publisherDivId);
              $publisherContainer[0].appendChild(publisherElement);

              // Start publishing (and set the size)
              var publisherProperties = {
                width: $publisherContainer.width(),
                height: $publisherContainer.height()
              };

              var publisher = TB.initPublisher(apiKey, publisherDivId, publisherProperties);
              session.publish(publisher);

              console.log("published");

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
                   self.disconnect();
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

  ChatWindow.prototype.disconnect = function() {
         if (typeof session != "undefined") {
              console.log("Disconnecting from chat...");
              session.disconnect();
              session = undefined;
              sessionId = undefined;
         }
    }

  return ChatWindow;
})();
          