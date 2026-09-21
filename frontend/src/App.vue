<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const view = ref('stays')
const hotelName = ref('')
const submittedQuery = ref('')
const results = ref([])
const searchState = ref('loading')
const searchError = ref('')
const users = ref([])
const selectedUserId = ref('')
const bookings = ref([])
const bookingState = ref('loading')
const bookingError = ref('')
const busyBookingId = ref('')
const deletePendingId = ref('')
const notice = ref('')
const selectedCity = ref('all')
const selectedPrice = ref('all')
const sortBy = ref('recommended')
const calendarOpen = ref(false)
const calendarOffset = ref(0)
const planningStart = ref('')
const planningEnd = ref('')
const weekdays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

async function api(path, options = {}) {
  const response = await fetch(path, options)
  if (response.status === 204) return null
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.detail ?? 'The request could not be completed.')
  return payload
}

async function searchHotels() {
  searchState.value = 'loading'
  searchError.value = ''
  notice.value = ''
  selectedCity.value = 'all'
  selectedPrice.value = 'all'
  sortBy.value = 'recommended'
  submittedQuery.value = hotelName.value.trim()
  try {
    const payload = await api(`/api/hotels/search?hotel_name=${encodeURIComponent(submittedQuery.value)}`)
    results.value = payload.results
    searchState.value = 'ready'
    view.value = 'stays'
  } catch (error) {
    searchError.value = error.message
    searchState.value = 'error'
  }
}

async function loadUsers() {
  try {
    const payload = await api('/api/users')
    users.value = payload.users
    selectedUserId.value = payload.users[0]?.user_id ?? ''
  } catch (error) {
    bookingError.value = error.message
    bookingState.value = 'error'
  }
}

async function loadBookings() {
  if (!selectedUserId.value) return
  bookingState.value = 'loading'
  bookingError.value = ''
  try {
    const payload = await api(`/api/bookings?user_id=${encodeURIComponent(selectedUserId.value)}`)
    bookings.value = payload.bookings
    bookingState.value = 'ready'
  } catch (error) {
    bookingError.value = error.message
    bookingState.value = 'error'
  }
}

watch(selectedUserId, loadBookings)
onMounted(() => {
  searchHotels()
  loadUsers()
})

const cityOptions = computed(() => [...new Set(results.value.map((item) => item.hotel.city))].sort())
const priceOptions = computed(() =>
  [...new Set(results.value.map((item) => Number(item.hotel.nightly_rate_usd)))].sort((a, b) => a - b),
)
const filteredResults = computed(() => {
  const matches = results.value.filter((item) => {
    const cityMatches = selectedCity.value === 'all' || item.hotel.city === selectedCity.value
    const rate = Number(item.hotel.nightly_rate_usd)
    const priceMatches = selectedPrice.value === 'all' || rate <= Number(selectedPrice.value)
    return cityMatches && priceMatches
  })
  if (sortBy.value === 'price-low') matches.sort((a, b) => Number(a.hotel.nightly_rate_usd) - Number(b.hotel.nightly_rate_usd))
  if (sortBy.value === 'price-high') matches.sort((a, b) => Number(b.hotel.nightly_rate_usd) - Number(a.hotel.nightly_rate_usd))
  return matches
})

function resetFilters() {
  selectedCity.value = 'all'
  selectedPrice.value = 'all'
  sortBy.value = 'recommended'
}

function stayNights(stay) {
  if (!stay?.check_in || !stay?.check_out) return null
  const days = (Date.parse(stay.check_out) - Date.parse(stay.check_in)) / 86400000
  return Number.isInteger(days) && days > 0 ? days : null
}

function money(value) {
  if (value === null || value === undefined || value === '') return '—'
  const amount = Number(value)
  return Number.isFinite(amount)
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount)
    : '—'
}

function stayTotal(item) {
  const rate = Number(item.hotel?.nightly_rate_usd)
  const nights = stayNights(item.stay)
  return Number.isFinite(rate) && nights ? money(rate * nights) : '—'
}

function dateLabel(value) {
  if (!value) return 'Date unavailable'
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T12:00:00Z`))
}

async function createBooking(item) {
  if (!selectedUserId.value) {
    bookingError.value = 'Choose a demo traveler before booking.'
    return
  }
  busyBookingId.value = item.stay.trip_id
  bookingError.value = ''
  try {
    const booking = await api('/api/bookings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: selectedUserId.value, trip_id: item.stay.trip_id }),
    })
    await loadBookings()
    view.value = 'bookings'
    notice.value = `Booking ${booking.booking_id} created. This is a simulation; no payment was taken.`
  } catch (error) {
    bookingError.value = error.message
  } finally {
    busyBookingId.value = ''
  }
}

async function cancelBooking(booking) {
  busyBookingId.value = booking.booking_id
  bookingError.value = ''
  try {
    await api(`/api/bookings/${encodeURIComponent(booking.booking_id)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'cancelled' }),
    })
    await loadBookings()
    notice.value = `Booking ${booking.booking_id} was cancelled and remains in history.`
  } catch (error) {
    bookingError.value = error.message
  } finally {
    busyBookingId.value = ''
  }
}

async function deleteBooking(booking) {
  busyBookingId.value = booking.booking_id
  bookingError.value = ''
  try {
    await api(`/api/bookings/${encodeURIComponent(booking.booking_id)}`, { method: 'DELETE' })
    await loadBookings()
    deletePendingId.value = ''
    notice.value = `Test booking ${booking.booking_id} was deleted.`
  } catch (error) {
    bookingError.value = error.message
  } finally {
    busyBookingId.value = ''
  }
}

function showView(nextView) {
  view.value = nextView
  notice.value = ''
  if (nextView === 'bookings') loadBookings()
}

const calendarMonths = computed(() => {
  const today = new Date()
  return [0, 1].map((step) => {
    const month = new Date(today.getFullYear(), today.getMonth() + calendarOffset.value + step, 1)
    const daysInMonth = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
    const cells = Array.from({ length: month.getDay() }, () => null)
    for (let day = 1; day <= daysInMonth; day += 1) {
      cells.push(`${month.getFullYear()}-${String(month.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`)
    }
    return {
      key: `${month.getFullYear()}-${month.getMonth()}`,
      title: new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' }).format(month),
      cells,
    }
  })
})

const planningLabel = computed(() =>
  planningStart.value && planningEnd.value
    ? `${dateLabel(planningStart.value)} – ${dateLabel(planningEnd.value)}`
    : 'Choose planning dates',
)

function choosePlanningDate(value) {
  if (!planningStart.value || planningEnd.value || value <= planningStart.value) {
    planningStart.value = value
    planningEnd.value = ''
  } else {
    planningEnd.value = value
  }
}
</script>

<template>
  <div class="app">
    <header class="site-header">
      <div class="site-header-inner">
        <button class="brand" type="button" @click="showView('stays')">
          <span class="brand-mark" aria-hidden="true">✦</span> expedia<span>rep</span>
        </button>
        <nav aria-label="Main navigation" class="main-nav">
          <button type="button" :class="{ active: view === 'stays' }" @click="showView('stays')">Explore stays</button>
          <button type="button" :class="{ active: view === 'bookings' }" @click="showView('bookings')">Booking history</button>
        </nav>
        <label class="traveler-picker">
          <span>Demo traveler</span>
          <select v-model="selectedUserId" aria-label="Demo traveler">
            <option v-for="user in users" :key="user.user_id" :value="user.user_id">{{ user.display_name }}</option>
          </select>
        </label>
      </div>
    </header>

    <main>
      <section class="hero" aria-labelledby="page-title">
        <div class="hero-inner">
          <div class="hero-copy">
            <p class="hero-kicker">Explore more, stay somewhere memorable</p>
            <h1 id="page-title">Find your next great stay.</h1>
            <p>Search real demo offers, compare fixed dates and prices, and plan a trip in a few simple steps.</p>
          </div>
          <div class="hero-art" aria-hidden="true">
            <svg viewBox="0 0 270 210" role="presentation">
              <circle cx="198" cy="55" r="35" fill="#ffd74d" />
              <path d="M10 180 Q72 86 133 180Z" fill="#78b5c2" />
              <path d="M78 180 Q164 54 266 180Z" fill="#b6d5d6" />
              <path d="M115 180V83q0-9 9-9h69q9 0 9 9v97" fill="#fff" />
              <path d="M126 74V49h66v25" fill="#f8bc54" />
              <path d="M140 49V37h40v12" fill="none" stroke="#103d6b" stroke-width="8" stroke-linejoin="round" />
              <path d="M134 99h18v22h-18zm30 0h18v22h-18zm-30 36h18v22h-18zm30 0h18v22h-18z" fill="#86c8d2" />
              <path d="M8 180h255" stroke="#0f3d6b" stroke-width="8" stroke-linecap="round" />
              <path d="M38 57l36-13m-18-11l18 11-12 16" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
        </div>
      </section>

      <div class="content-wrap">
        <section class="search-card" aria-labelledby="search-title">
          <div class="search-card-heading">
            <div>
              <p class="eyebrow">Find a hotel</p>
              <h2 id="search-title">Where would you like to go?</h2>
            </div>
            <span class="simulation-pill">Demo booking · no payment</span>
          </div>
          <form class="search-form" @submit.prevent="searchHotels">
            <label class="field hotel-field">
              <span>Hotel name</span>
              <span class="field-control"><span aria-hidden="true">⌕</span><input v-model="hotelName" type="search" placeholder="Try Inn, Trail, or Harbor" /></span>
            </label>
            <div class="field date-field">
              <span>Planning dates</span>
              <button class="date-trigger" type="button" :aria-expanded="calendarOpen" @click="calendarOpen = !calendarOpen">
                <span aria-hidden="true">▦</span> {{ planningLabel }}
              </button>
            </div>
            <button class="primary-button search-button" type="submit" :disabled="searchState === 'loading'">
              {{ searchState === 'loading' ? 'Searching…' : 'Search stays' }}
            </button>
          </form>
          <p class="field-note">Planning dates help you compare options; each offer keeps the fixed dates shown below.</p>
          <div v-if="calendarOpen" class="calendar" role="dialog" aria-label="Choose planning dates">
            <div class="calendar-toolbar">
              <strong>Select planning dates</strong>
              <div>
                <button type="button" aria-label="Previous months" @click="calendarOffset -= 1">‹</button>
                <button type="button" aria-label="Next months" @click="calendarOffset += 1">›</button>
                <button type="button" aria-label="Close calendar" @click="calendarOpen = false">✕</button>
              </div>
            </div>
            <div class="calendar-months">
              <div v-for="month in calendarMonths" :key="month.key" class="calendar-month">
                <h3>{{ month.title }}</h3>
                <div class="calendar-grid">
                  <span v-for="day in weekdays" :key="day" class="weekday">{{ day }}</span>
                  <template v-for="(day, index) in month.cells" :key="day ?? `blank-${index}`">
                    <span v-if="!day" aria-hidden="true"></span>
                    <button v-else type="button" :class="{ selected: day === planningStart || day === planningEnd, inRange: planningStart && planningEnd && day > planningStart && day < planningEnd }" :aria-label="dateLabel(day)" @click="choosePlanningDate(day)">{{ Number(day.slice(-2)) }}</button>
                  </template>
                </div>
              </div>
            </div>
            <p>Select a start and end date. This planning tool does not change the fixed stay offers.</p>
          </div>
        </section>

        <p v-if="notice" class="notice success" role="status">{{ notice }}</p>
        <p v-if="bookingError" class="notice error" role="alert">{{ bookingError }}</p>

        <template v-if="view === 'stays'">
          <section class="section-head" aria-labelledby="results-title">
            <div><p class="eyebrow">Hotels and stays</p><h2 id="results-title">{{ submittedQuery ? `Results for “${submittedQuery}”` : 'Explore available stays' }}</h2></div>
            <span v-if="searchState === 'ready'" class="result-count">{{ filteredResults.length }} stay{{ filteredResults.length === 1 ? '' : 's' }}</span>
          </section>
          <p v-if="searchState === 'loading'" class="empty-state" role="status">Loading available stays…</p>
          <p v-else-if="searchState === 'error'" class="empty-state error" role="alert">{{ searchError }}</p>
          <template v-else>
            <div v-if="results.length" class="filters">
              <label>City<select v-model="selectedCity" aria-label="Filter by city"><option value="all">All cities</option><option v-for="city in cityOptions" :key="city" :value="city">{{ city }}</option></select></label>
              <label>Nightly rate<select v-model="selectedPrice" aria-label="Filter by nightly rate"><option value="all">Any price</option><option v-for="price in priceOptions" :key="price" :value="price">Up to {{ money(price) }}</option></select></label>
              <label>Sort<select v-model="sortBy" aria-label="Sort stays"><option value="recommended">Recommended</option><option value="price-low">Price: low to high</option><option value="price-high">Price: high to low</option></select></label>
              <button v-if="selectedCity !== 'all' || selectedPrice !== 'all' || sortBy !== 'recommended'" class="text-button" type="button" @click="resetFilters">Clear filters</button>
            </div>
            <p v-if="!results.length" class="empty-state" role="status">No matching hotel stays were found.</p>
            <p v-else-if="!filteredResults.length" class="empty-state" role="status">No stays match these filters. <button class="text-button" type="button" @click="resetFilters">Clear filters</button></p>
            <div v-else class="stay-list">
              <article v-for="(item, index) in filteredResults" :key="item.stay.trip_id" class="stay-card">
                <div class="stay-illustration" :class="`tone-${index % 4}`" role="img" :aria-label="`Illustrated placeholder for ${item.hotel.hotel_name}`">
                  <span class="illustration-sun"></span><span class="illustration-hill"></span><span class="illustration-building">▥</span>
                  <span class="photo-note">Illustration · no photo supplied</span>
                </div>
                <div class="stay-main">
                  <p class="stay-id">Stay {{ item.stay.trip_id }} · Hotel {{ item.hotel.hotel_id }}</p>
                  <h3>{{ item.hotel.hotel_name }}</h3>
                  <p class="location">⌾ {{ item.hotel.city }}, {{ item.hotel.state }}</p>
                  <p class="trip-name">{{ item.stay.trip_name }}</p>
                  <p class="stay-dates">{{ dateLabel(item.stay.check_in) }} – {{ dateLabel(item.stay.check_out) }} <span v-if="stayNights(item.stay)">· {{ stayNights(item.stay) }} nights</span></p>
                </div>
                <div class="stay-price">
                  <span>From</span><strong>{{ money(item.hotel.nightly_rate_usd) }}</strong><small>per night</small>
                  <p>{{ stayTotal(item) }} stay total*</p>
                  <button class="primary-button" type="button" :disabled="busyBookingId === item.stay.trip_id" @click="createBooking(item)">{{ busyBookingId === item.stay.trip_id ? 'Booking…' : 'Book this stay' }}</button>
                </div>
              </article>
            </div>
            <p v-if="filteredResults.length" class="price-disclaimer">* Simulated total is nightly rate × nights. Taxes and fees are not in the supplied data. Booking does not reserve inventory or charge a card.</p>
          </template>
        </template>

        <section v-else class="history-section" aria-labelledby="history-title">
          <div class="section-head"><div><p class="eyebrow">Your demo trips</p><h2 id="history-title">Booking history</h2></div><span v-if="bookingState === 'ready'" class="result-count">{{ bookings.length }} booking{{ bookings.length === 1 ? '' : 's' }}</span></div>
          <p class="history-intro">Bookings are stored locally for this demo traveler. Cancelling keeps a record in history.</p>
          <p v-if="bookingState === 'loading'" class="empty-state" role="status">Loading booking history…</p>
          <p v-else-if="bookingState === 'error'" class="empty-state error" role="alert">{{ bookingError }}</p>
          <p v-else-if="!bookings.length" class="empty-state" role="status">No bookings yet for this traveler. Explore stays to create one.</p>
          <div v-else class="booking-list">
            <article v-for="booking in bookings" :key="booking.booking_id" class="booking-card">
              <div class="booking-content">
                <div class="booking-meta"><span class="booking-id">{{ booking.booking_id }}</span><span :class="['status-badge', booking.status]">{{ booking.status }}</span><span v-if="booking.source === 'created'" class="demo-badge">test booking</span></div>
                <h3>{{ booking.hotel?.hotel_name ?? 'Hotel unavailable' }}</h3>
                <p>{{ booking.stay?.trip_name ?? booking.trip_id }} · {{ booking.hotel?.city }}, {{ booking.hotel?.state }}</p>
                <p class="booking-dates">{{ dateLabel(booking.stay?.check_in) }} – {{ dateLabel(booking.stay?.check_out) }} · Booked {{ dateLabel(booking.booked_on) }}</p>
              </div>
              <div class="booking-actions">
                <button v-if="booking.status === 'confirmed'" class="secondary-button" type="button" :disabled="busyBookingId === booking.booking_id" @click="cancelBooking(booking)">Cancel booking</button>
                <template v-if="booking.source === 'created'">
                  <button v-if="deletePendingId !== booking.booking_id" class="delete-button" type="button" :disabled="busyBookingId === booking.booking_id" @click="deletePendingId = booking.booking_id">Delete test booking</button>
                  <div v-else class="delete-confirm">
                    <span>Remove this test booking?</span>
                    <button class="delete-button" type="button" :disabled="busyBookingId === booking.booking_id" @click="deleteBooking(booking)">Confirm delete</button>
                    <button class="text-button" type="button" @click="deletePendingId = ''">Keep booking</button>
                  </div>
                </template>
              </div>
            </article>
          </div>
        </section>
      </div>
    </main>
    <footer class="site-footer">Expedia Rep · classroom prototype · simulated bookings only</footer>
  </div>
</template>
