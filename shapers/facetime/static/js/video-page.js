// Initialize API key, session, and token...
// Think of a session as a room, and a token as the key to get in to the room
// Sessions and tokens are generated on your server and passed down to the client
var apiKey = "41805792";

var globalFaceTime = window.globalFacetime = {};
globalFaceTime.user = "" + Math.floor(Math.random()*100000);

$.ajax({
  method: "GET",
  url: "/connect",
  dataType: "json",
  success: function(data) {
      console.log("Got data from server: ");
      console.log(data);

      var session = TB.initSession(data.sessionId);
          globalFaceTime.sessionId = data.sessionId;
          globalFaceTime.session = session;

      console.log("session");
      console.log(session);

      function connectToStreams(streams) {
          for (var i = 0; i < streams.length; i++) {
              var stream = streams[i];
              if (stream.connection.connectionId != session.connection.connectionId) {
                  var subscriber = session.subscribe(stream, "mySubscriberDiv"); 
                  var subscriberFlashElement = document.getElementById(subscriber.id);

                  subscriberFlashElement.width = $("#mySubscriberDivContainer").width();                         
                  subscriberFlashElement.height = $("#mySubscriberDivContainer").height();
              }
          }
      }

      function sessionConnectedHandler(event) {
          console.log("in sessionConnectedHandler");

          var publisherElement = document.createElement("div");
          publisherElement.setAttribute("id","publisherDiv");
          $("#myPublisherDivContainer")[0].appendChild(publisherElement);

          var publisherProperties = {
            width: $("#myPublisherDivContainer").width(),
            height: $("#myPublisherDivContainer").height()
          };

          var publisher = TB.initPublisher(apiKey, 'publisherDiv',publisherProperties);
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
               processChatDisconnected();
          }

          function sessionDisconnectedHandler(event) {
               console.log("sessionDisconnectedHandler");
               console.log(event);
               processChatDisconnected();
          }

          function connectionDestroyedHandler(event) {
               console.log("sessionDestroyedHandler");
               console.log(event);
               processChatDisconnected();
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

function processChatDisconnected() {
     if (typeof globalFaceTime.session != "undefined") {
          console.log("Disconnecting from chat...");
          globalFaceTime.session.disconnect();
          globalFaceTime.session = undefined;
          globalFaceTime.sessionId = undefined;
     }
}

MAXIMUM_HEARTBEAT_AGE_BEFORE_DISCONNECT_MILLI = 10000;

function processHeartbeats(now,heartbeats) {
     var nowDate = new Date(now);

     //console.log("HEARTBEAT: Processing ");
     //console.log(heartbeats);

     for (var user in heartbeats) {
          var lastHeartbeat = new Date(heartbeats[user]);

          var staleness = nowDate - lastHeartbeat;
          //console.log("HEARTBEAT: Staleness of " + user + " is " + staleness);

          if (staleness >= MAXIMUM_HEARTBEAT_AGE_BEFORE_DISCONNECT_MILLI) {
               console.log("Chat is stale ("+staleness+"). Disconnect.");
               processChatDisconnected();
          }
     }
}

(function(){
     if (typeof globalFaceTime.sessionId != 'undefined') {
          $.ajax({
               method: "GET",
               dataType: "JSON",
               url: "/heartbeat",
               data: {
                    sessionId:globalFaceTime.sessionId,
                    user:globalFaceTime.user
               },
               success: function(data) {
                    processHeartbeats(data.now,data.heartbeats);
               }
          });
     }

    setTimeout(arguments.callee, 1000);
})();      
          