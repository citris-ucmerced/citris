
async function populateEvents(eventsContainer, onlyRecentEvent) {
  var text = await $.get("events.csv");    
  var data = $.csv.toObjects(text);
  for (var i = 0; i < data.length; i++) {
    if(data[i].ID.toString() === "OLD"){
      if(onlyRecentEvent){
        return;
      }
    }
    else{
      var img = await loadImage(data[i]);

      var isVert = true;
      if (img !== null) {
        isVert = img.height > img.width;
      }
        
      var event = $.parseHTML(
        '<div>' +
        '<figure class="event '  +  ((isVert) ? 'event_vert' : 'event_horiz') +'">' +
            '<figcaption>' +
                (((data[i].HTML_ID).toString() === '') ? '<h3>' + data[i].TITLE + '</h3>' : '<h3><a href="/events/' + data[i].HTML_ID + '" target="_blank">' + data[i].TITLE + '</a></h3>') +
                '<p>' + data[i].TEXT + '</p>' +
                (((data[i].LOCATION).toString() === '') ? '' :  '<p><strong>Location:</strong> ' + data[i].LOCATION + '</p>') +
                (((data[i].EVENTABLE).toString() === '') ? '' :  '<center><p>' + data[i].EVENTABLE + '</p></center>') +
                (((data[i].PDF_ID).toString() === '') ? '' :  '<center><a href="events/pdfs/' + data[i].PDF_ID + '.pdf" download>Download PDF</a></center>') +
                (((data[i].BUTTON_TEXT).toString() === 'NO_BUTTON') ? '' : ((data[i].BUTTON_TEXT).toString() === '') ? '<center><a class="button" href="' + data[i].LINK + '" target="_blank"> Click Here </a></center>' : '<center><a class="button" href="' + data[i].LINK + '" target="_blank">' +  data[i].BUTTON_TEXT + '</a></center>') +
                '<footer>'+ 
                    '<div class="event_date">' + data[i].DATES + '</div>'+
                '</footer>'+
            '</figcaption>'+
        '</figure>'+
        '<br>'+
        '</div>'
      );

      if(img !== null){
        $(event).children("figure").prepend(img); 
      }
      eventsContainer.append(event);
    } 
  }
}

function loadImage(eventData){
  return new Promise ((resolve, reject) =>{
    if(eventData.ID.toString() === ""){

      resolve(null);
    }
    else{
      var img = new Image();
      img.src = '/images/events/' + eventData.ID + '.jpg';
      img.onload = () => resolve(img);
      img.onerror = reject;
    }
  })
}
