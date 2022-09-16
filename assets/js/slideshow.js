var slide1 = new Image();
    slide1.src = '../../images/banners/banner.jpg';
var slide2 = new Image();
    slide2.src = '../../images/banners/Beginnings_Jan4_morning-1.jpg';
var slide3 = new Image();
    slide3.src = '../../images/banners/SREbanner.jpg';

var int = setInterval(function() {
    if (slide1.complete && slide2.complete && slide3.complete) {
        clearInterval(int);
        document.getElementById('slide1').style.backgroundImage = 'url(' + slide1.src + ')';
        document.getElementById('slide1contrast').style.backgroundImage = 'linear-gradient(to bottom, #4d82b75b 0, #4d82b794 100%), url(' + slide1.src + ')';
        document.getElementById('slide1contrastafter').style.backgroundImage = 'linear-gradient(to bottom, #4d82b75b 0, #4d82b794 100%), url(' + slide1.src + ')';
        document.getElementById('slide2').style.backgroundImage = 'url(' + slide2.src + ')';
        document.getElementById('slide2contrast').style.backgroundImage = 'linear-gradient(to bottom, #4d82b75b 0, #4d82b794 100%), url(' + slide2.src + ')';
        document.getElementById('slide2contrastafter').style.backgroundImage = 'linear-gradient(to bottom, #4d82b75b 0, #4d82b794 100%), url(' + slide2.src + ')';
        document.getElementById('slide3').style.backgroundImage = 'url(' + slide3.src + ')';
        document.getElementById('slide3contrast').style.backgroundImage = 'linear-gradient(to bottom, #4d82b75b 0, #4d82b794 100%), url(' + slide3.src + ')';
        document.getElementById('slide3contrastafter').style.backgroundImage = 'linear-gradient(to bottom, #4d82b75b 0, #4d82b794 100%), url(' + slide3.src + ')';
    }
}, 3000);