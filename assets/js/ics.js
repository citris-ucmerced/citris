const icsFormatter = () => {
  if (
    navigator.userAgent.indexOf('MSIE') > -1 &&
    navigator.userAgent.indexOf('MSIE 10') === -1
  ) {
    console.log('Unsupported Browser')
    return
  }

  const SEPARATOR = navigator.appVersion.indexOf('Win') !== -1 ? '\r\n' : '\n'
  const calendarEvents = []
  const calendarStart = ['BEGIN:VCALENDAR', 'VERSION:2.0'].join(SEPARATOR)
  const calendarEnd = `${SEPARATOR}END:VCALENDAR`

  return {
    /**
     * Returns events array
     * @return {array} Events
     */
    events: () => calendarEvents,

    /**
     * Returns calendar
     * @return {string} Calendar in iCalendar format
     */
    calendar: () =>
      calendarStart + SEPARATOR + calendarEvents.join(SEPARATOR) + calendarEnd,

    /**
     * Add event to the calendar
     * @param  {string} subject     Subject/Title of event
     * @param  {string} description Description of event
     * @param  {string} location    Location of event
     * @param  {string} begin       Beginning date of event
     * @param  {string} stop        Ending date of event
     */
    addEvent: (subject, description, location, begin, stop) => {
      // I'm not in the mood to make these optional... So they are all required
      if (
        typeof subject === 'undefined' ||
        typeof description === 'undefined' ||
        typeof location === 'undefined' ||
        typeof begin === 'undefined' ||
        typeof stop === 'undefined'
      ) {
        return false
      }

      //TODO add time and time zone? use moment to format?
      const start_date = new Date(begin)
      const end_date = new Date(stop)

      const start_year = `0000${start_date.getFullYear().toString()}`.slice(-4)
      const start_month = `00${(start_date.getMonth() + 1).toString()}`.slice(
        -2,
      )
      const start_day = `00${start_date.getDate().toString()}`.slice(-2)
      const start_hours = `00${start_date.getHours().toString()}`.slice(-2)
      const start_minutes = `00${start_date.getMinutes().toString()}`.slice(-2)
      const start_seconds = `00${start_date.getMinutes().toString()}`.slice(-2)

      const end_year = `0000${end_date.getFullYear().toString()}`.slice(-4)
      const end_month = `00${(end_date.getMonth() + 1).toString()}`.slice(-2)
      const end_day = `00${end_date.getDate().toString()}`.slice(-2)
      const end_hours = `00${end_date.getHours().toString()}`.slice(-2)
      const end_minutes = `00${end_date.getMinutes().toString()}`.slice(-2)
      const end_seconds = `00${end_date.getMinutes().toString()}`.slice(-2)

      // Since some calendars don't add 0 second events, we need to remove time if there is none...
      let start_time = ''
      let end_time = ''
      if (start_minutes + start_seconds + end_minutes + end_seconds !== 0) {
        start_time = `T${start_hours}${start_minutes}${start_seconds}`
        end_time = `T${end_hours}${end_minutes}${end_seconds}`
      }

      const start = start_year + start_month + start_day + start_time
      const end = end_year + end_month + end_day + end_time

      const calendarEvent = [
        'BEGIN:VEVENT',
        'CLASS:PUBLIC',
        `DESCRIPTION:${description}`,
        `DTSTART;VALUE=DATE:${start}`,
        `DTEND;VALUE=DATE:${end}`,
        `LOCATION:${location}`,
        `SUMMARY;LANGUAGE=en-us:${subject}`,
        'TRANSP:TRANSPARENT',
        'END:VEVENT',
      ].join(SEPARATOR)

      calendarEvents.push(calendarEvent)
      return calendarEvent
    },

    /**
     * Download calendar using the saveAs function from filesave.js
     * @param  {string} filename Filename
     * @param  {string} ext      Extention
     */
    download: (filename, ext) => {
      if (calendarEvents.length < 1) {
        return false
      }

      ext = typeof ext !== 'undefined' ? ext : '.ics'
      filename = typeof filename !== 'undefined' ? filename : 'calendar'
      const calendar =
        calendarStart + SEPARATOR + calendarEvents.join(SEPARATOR) + calendarEnd
      window.location = `data:text/calendar;charset=utf8,${escape(calendar)}`
    },
  }
}

if (typeof define === 'function' && define.amd) {
  /* AMD Format */
  define('icsFormatter', [], () => icsFormatter())
} else if (typeof module === 'object' && module.exports) {
  /* CommonJS Format */
  module.exports = icsFormatter()
} else {
  /* Plain Browser Support */
  this.myModule = icsFormatter()
}
