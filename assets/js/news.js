const newsCardTemplate = document.querySelector("[news-card]")
const newsCardContainer = document.querySelector(".news-cards-container")

let cards = []

/*
    @brief:
        This function reads from a csv file that stores all news articles
        It then iterates through the data to populate the news.html with
        news stories in the form of cards.
    
    @params: 
        none
*/
$(function () {
    
    // read csv file
    $.get("/news.csv").then((text) => {
        
        // convert text into a manageable variable
        var data = $.csv.toObjects(text);

        for (var i = 0; i < data.length; i++) {

            // main component that is based off template in news.html
            const card = newsCardTemplate.content.cloneNode(true).children[0]
            
            // additional elements in card (note we are calling card here)
            const image = card.querySelector("[news-card-image]")
            const header = card.querySelector("[news-card-header]")
            const paragraph = card.querySelector("[news-card-paragraph]")
            const footer = card.querySelector("[news-card-footer]")
            const link = card.querySelector("[news-card-link]")

            // handler for null images
            if (data[i].ID.toString() === '')
            {
                image.src = "images/favicon.png"
                image.classList.add("news-card__image")
            } else {
                image.src = "images/news/" + data[i].ID + ".jpg"
            }
            image.alt = ""

            // transfer current row content onto card
            header.textContent = data[i].TITLE
            paragraph.textContent = data[i].DESCRIPTION
            footer.textContent = data[i].DATE
            link.href = data[i].LINK

            // add card to DOM
            newsCardContainer.append(card)

            // store card for searchability purposes
            cards.push({header: data[i].TITLE, paragraph: data[i].DESCRIPTION, date: data[i].DATE, element: card})
        }
    })
})

/*
    @brief:
        This event listener watches the input element in the news.html.
        Everytime there is a change in the input element or search bar
        then the visibility of the news cards change depending on user
        criteria. All comparisons with strings are in lowercase
        
    @params:
        {event} e
*/
$("#search").on("input", (e) => {

    const value = e.target.value.toLowerCase()

    cards.forEach((card) => {
        const isVisible = 
            card.header.toLowerCase().includes(value) ||
            card.paragraph.toLowerCase().includes(value) ||
            card.date.toLowerCase().includes(value)
        
        if(isVisible) {
            // show
            card.element.style.display = "inline-block"
        } else {
            // hide
            card.element.style.display = "none"
        }
    })
})