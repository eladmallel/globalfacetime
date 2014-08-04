var EVENT_INFO_DEFAULTS = {
    startIn: 0,
    eventLength: 1000*3600,
    timePerPerson: 1000*60*7,
}

var PERSON_TIMER_RESOLUTION = 1000;
var EVENT_TIMER_RESOLUTION = 1000;

function ChatStateMachine(handleEvent) {
    var self = this;

    self.handleEvent = handleEvent;
    self.chatting = false;
    self.started = false;
    self.ended = false;

    // This sets up the chat event timers
    self.start = function(eventInfo) {
        self.eventInfo = $.extend({},EVENT_INFO_DEFAULTS,eventInfo);

        self.initalTime = new Date().getTime();

        if (self.eventInfo.startIn > 0) {
            self.handleEvent('eventEarly',self.eventInfo.startIn);
            self._eventTick(); // Start event timer
        } else if (self.eventInfo.startIn + self.eventInfo.eventLength > 0) {
            self.started = true;
            self.handleEvent('eventLate',self.eventInfo.startIn);
            self._eventTick(); // Start event timer
        } else {
            self.started = true;
            self.ended = true;
            self.handleEvent('eventAlreadyDone',self.eventInfo.startIn + self.eventInfo.eventLength);
        }
    }

    self.startChat = function() {
        // Stop an active chat
        if ( self.chatting ) {
            self.endChat();
        }

        self.personStartTime = new Date().getTime();
        self.chatting = true;

        self.handleEvent('chatStart',self.eventInfo.timePerPerson);

        // Start the person
        self._personTick();
    }

    self.endChat = function() {
        // Clear previous timeouts
        if ( self.chatting ) {
            self.chatting = false;
            window.clearTimeout(self.personTimeout);
            self.handleEvent('chatEnd');
            
        }
    }

    self._eventTick = function() {
        var currTime = new Date().getTime();

        var sinceInit = currTime - self.initalTime;

        var tillStart =  self.eventInfo.startIn - sinceInit;
        var tillEnd = self.eventInfo.startIn + self.eventInfo.eventLength - sinceInit;

        if ( !self.started ) {
            if ( tillStart <= 0) {
                self.started = true;
                self.handleEvent('eventStart',tillEnd);
            } else {
                self.handleEvent('eventStartIn',tillStart);
            }
        } else if ( !self.ended ) {
            if ( tillEnd <= 0 ) {
                self.ended = true;
                self.handleEvent('eventEnd');
            } else {
                self.handleEvent('eventInProgress',tillEnd);
            }
        }

        // Run us again in a little while
        if ( !self.started || !self.ended ) {
            self.eventTimeout = window.setTimeout(self._eventTick,EVENT_TIMER_RESOLUTION);
        }
    }

    self._personTick = function() {
        // Not chatting? Then nm
        if (!self.chatting) {
            return;
        }

        var currTime = new Date().getTime();

        var sinceChat = currTime - self.personStartTime;
        var tillEnd =  self.eventInfo.timePerPerson - sinceChat;

        //console.log("time till the end of this chat: " + tillEnd);

        if ( tillEnd <= 0) {
            self.chatting = false;
            window.analytics.track("Chat Auto Skipped");
            self.handleEvent('chatEnd');
        } else {
            self.handleEvent('chatInProgress',tillEnd);
        }
        
        // Run us again in a little while
        if ( self.chatting ) {
            self.personTimeout = window.setTimeout(self._personTick,PERSON_TIMER_RESOLUTION);
        }

    }
}
