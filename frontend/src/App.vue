<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import TravelChat from './components/TravelChat.vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const view = ref('stays')
const hotelName = ref('')
const submittedQuery = ref('')
const results = ref([])
const searchCount = ref(0)
const resultsUserId = ref(null)
const searchState = ref('loading')
const searchError = ref('')
const authUser = ref(null)
const authMode = ref('login')
const authUsername = ref('')
const authPassword = ref('')
const authDisplayName = ref('')
const authError = ref('')
const authBusy = ref(false)
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
const zipPostcode = ref('16802')
const zipState = ref('idle')
const zipLocation = ref(null)
const zipError = ref('')
const zipSource = ref('')
const savedProviderIds = ref(new Set())
const pendingHotelIds = ref(new Set())
const zipActionFeedback = ref({ type: '', text: '' })
const zipMapElement = ref(null)
const selectedZipHotelId = ref('')
const selectedZipHotel = computed(() => zipLocation.value?.hotels?.find((hotel) => zipHotelId(hotel) === selectedZipHotelId.value) ?? null)
const weekdays = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']
let zipMap = null
let zipCenterMarker = null
const zipHotelMarkers = new Map()

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: 'same-origin', ...options })
  if (response.status === 204) return null
  let payload = {}
  try {
    payload = await response.json()
  } catch {
    if (response.ok) throw new Error('The server returned an unreadable response.')
  }
  if (!response.ok) {
    const error = new Error(payload.detail ?? 'The request could not be completed.')
    error.status = response.status
    throw error
  }
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
  const searchingUserId = authUser.value?.user_id ?? null
  try {
    const payload = await api(`/api/hotels/search?hotel_name=${encodeURIComponent(submittedQuery.value)}`)
    results.value = payload.results
    searchCount.value = payload.matching_searches_today
    resultsUserId.value = searchingUserId
    searchState.value = 'ready'
    view.value = 'stays'
  } catch (error) {
    searchError.value = error.message
    searchState.value = 'error'
  }
}

async function lookupZip() {
  zipState.value = 'loading'
  zipLocation.value = null
  zipError.value = ''
  zipSource.value = ''
  zipActionFeedback.value = { type: '', text: '' }
  const postcode = zipPostcode.value.trim()
  if (!/^\d{5}$/.test(postcode)) {
    zipError.value = 'Enter a five-digit U.S. ZIP code.'
    zipState.value = 'invalid'
    return
  }
  try {
    let local
    try {
      local = await api(`/api/saved-hotels?postcode=${encodeURIComponent(postcode)}`)
    } catch (error) {
      throw new Error(`Could not check locally saved hotels: ${error.message}`, { cause: error })
    }
    savedProviderIds.value = new Set(local.saved_provider_ids ?? [])
    if (local.hotels?.length) {
      zipLocation.value = local
      zipSource.value = 'local'
      zipState.value = 'results'
      return
    }

    zipLocation.value = await api(`/api/demo/zip-location?postcode=${encodeURIComponent(postcode)}`)
    zipSource.value = 'api'
    zipState.value = zipLocation.value.hotels?.length ? 'results' : 'no-results'
  } catch (error) {
    if (error.status === 404) {
      zipError.value = 'Geoapify could not confirm this as the requested U.S. ZIP code. No hotel search was performed.'
      zipState.value = 'unresolved'
    } else {
      zipError.value = error.message || 'The ZIP lookup request failed. Please try again.'
      zipState.value = 'failure'
    }
  }
}

function setPendingHotel(providerId, pending) {
  const next = new Set(pendingHotelIds.value)
  if (pending) next.add(providerId)
  else next.delete(providerId)
  pendingHotelIds.value = next
}

function setZipFeedback(type, text) {
  zipActionFeedback.value = { type, text }
}

async function addHotelToLocal(hotel) {
  const providerId = hotel.provider_id
  if (!providerId || savedProviderIds.value.has(providerId) || pendingHotelIds.value.has(providerId)) return
  setPendingHotel(providerId, true)
  setZipFeedback('', '')
  try {
    await api('/api/saved-hotels', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hotel: {
          provider_id: providerId,
          name: hotel.name ?? null,
          address: hotel.address ?? null,
          latitude: hotel.latitude,
          longitude: hotel.longitude,
        },
        location: {
          postcode: zipLocation.value.postcode,
          country_code: zipLocation.value.country_code,
          latitude: zipLocation.value.latitude,
          longitude: zipLocation.value.longitude,
          locality: zipLocation.value.locality ?? null,
        },
      }),
    })
    savedProviderIds.value = new Set([...savedProviderIds.value, providerId])
    setZipFeedback('success', `${hotel.name || 'Hotel'} saved locally for ZIP ${zipLocation.value.postcode}.`)
  } catch (error) {
    setZipFeedback('error', `Could not save ${hotel.name || 'this hotel'} locally: ${error.message}`)
  } finally {
    setPendingHotel(providerId, false)
  }
}

async function removeHotelFromLocal(hotel) {
  const providerId = hotel.provider_id
  if (!providerId || !savedProviderIds.value.has(providerId) || pendingHotelIds.value.has(providerId)) return
  setPendingHotel(providerId, true)
  setZipFeedback('', '')
  try {
    await api(`/api/saved-hotels/${encodeURIComponent(providerId)}`, { method: 'DELETE' })
    const nextSavedIds = new Set(savedProviderIds.value)
    nextSavedIds.delete(providerId)
    savedProviderIds.value = nextSavedIds
    if (zipSource.value === 'local' && zipLocation.value) {
      zipLocation.value = {
        ...zipLocation.value,
        hotels: zipLocation.value.hotels.filter((savedHotel) => savedHotel.provider_id !== providerId),
      }
      if (selectedZipHotelId.value === providerId) selectedZipHotelId.value = ''
      if (!zipLocation.value.hotels.length) zipState.value = 'no-results'
    }
    setZipFeedback('success', `${hotel.name || 'Hotel'} removed from local storage.`)
  } catch (error) {
    setZipFeedback('error', `Could not remove ${hotel.name || 'this hotel'}: ${error.message}`)
  } finally {
    setPendingHotel(providerId, false)
  }
}

async function loadSession() {
  try {
    const payload = await api('/api/auth/me')
    authUser.value = payload.user
  } catch (error) {
    authError.value = error.message
  }
}

async function loadBookings() {
  if (!authUser.value) return
  bookingState.value = 'loading'
  bookingError.value = ''
  try {
    const payload = await api('/api/bookings')
    bookings.value = payload.bookings
    bookingState.value = 'ready'
  } catch (error) {
    bookingError.value = error.message
    bookingState.value = 'error'
  }
}

onMounted(async () => {
  await loadSession()
  await searchHotels()
})

async function submitAccount() {
  authBusy.value = true
  authError.value = ''
  try {
    if (authMode.value === 'register') {
      await api('/api/auth/register', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: authUsername.value, password: authPassword.value, display_name: authDisplayName.value }),
      })
      authPassword.value = ''
      authMode.value = 'login'
      notice.value = 'Demo account created. Sign in to personalize searches and see your bookings.'
    } else {
      const payload = await api('/api/auth/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: authUsername.value, password: authPassword.value }),
      })
      authUser.value = payload.user
      authPassword.value = ''
      view.value = 'stays'
      notice.value = `Signed in as ${payload.user.username}. Submit a hotel search to see your personalized rate.`
    }
  } catch (error) {
    authError.value = error.message
  } finally {
    authBusy.value = false
  }
}

async function logout() {
  try {
    await api('/api/auth/logout', { method: 'POST' })
    authUser.value = null
    bookings.value = []
    await searchHotels()
    notice.value = 'Signed out. Searches now show base rates.'
  } catch (error) {
    authError.value = error.message
  }
}

const cityOptions = computed(() => [...new Set(results.value.map((item) => item.hotel.city))].sort())
const priceOptions = computed(() =>
  [...new Set(results.value.map((item) => Number(item.pricing.displayed_nightly_rate_usd)))].sort((a, b) => a - b),
)
const filteredResults = computed(() => {
  const matches = results.value.filter((item) => {
    const cityMatches = selectedCity.value === 'all' || item.hotel.city === selectedCity.value
    const rate = Number(item.pricing.displayed_nightly_rate_usd)
    const priceMatches = selectedPrice.value === 'all' || rate <= Number(selectedPrice.value)
    return cityMatches && priceMatches
  })
  if (sortBy.value === 'price-low') matches.sort((a, b) => Number(a.pricing.displayed_nightly_rate_usd) - Number(b.pricing.displayed_nightly_rate_usd))
  if (sortBy.value === 'price-high') matches.sort((a, b) => Number(b.pricing.displayed_nightly_rate_usd) - Number(a.pricing.displayed_nightly_rate_usd))
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
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 2 }).format(amount)
    : '—'
}

function stayTotal(item) {
  const rate = Number(item.pricing?.displayed_nightly_rate_usd)
  const nights = stayNights(item.stay)
  return Number.isFinite(rate) && nights ? money(rate * nights) : '—'
}

function dateLabel(value) {
  if (!value) return 'Date unavailable'
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T12:00:00Z`))
}

function distanceLabel(value) {
  const distance = Number(value)
  return Number.isFinite(distance) ? `${(distance / 1000).toFixed(1)} km` : '—'
}

function zipHotelId(hotel) {
  return hotel.provider_id || `${hotel.name}|${hotel.latitude}|${hotel.longitude}`
}

function isHotelSaved(hotel) {
  return Boolean(hotel.provider_id && savedProviderIds.value.has(hotel.provider_id))
}

function isHotelPending(hotel) {
  return Boolean(hotel.provider_id && pendingHotelIds.value.has(hotel.provider_id))
}

function formatDemoRate(cents) {
  return money(Number(cents) / 100)
}

function hotelMarkerIcon(selected = false) {
  return L.divIcon({
    className: 'zip-map-marker-shell',
    html: `<span class="zip-map-marker${selected ? ' selected' : ''}"></span>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  })
}

function selectZipHotel(hotel) {
  selectedZipHotelId.value = zipHotelId(hotel)
}

function clearZipHotelMarkers() {
  for (const marker of zipHotelMarkers.values()) marker.remove()
  zipHotelMarkers.clear()
}

watch(zipLocation, async (location) => {
  await nextTick()
  if (!location || !zipMapElement.value) {
    clearZipHotelMarkers()
    zipCenterMarker?.remove()
    zipCenterMarker = null
    zipMap?.remove()
    zipMap = null
    selectedZipHotelId.value = ''
    return
  }

  const center = [location.latitude, location.longitude]
  if (!zipMap) {
    zipMap = L.map(zipMapElement.value, { scrollWheelZoom: false }).setView(center, 13)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(zipMap)
  } else {
    zipMap.setView(center, 13)
  }

  clearZipHotelMarkers()
  zipCenterMarker?.remove()
  zipCenterMarker = L.circleMarker(center, {
    radius: 7,
    color: '#fff',
    weight: 2,
    fillColor: '#164f83',
    fillOpacity: 1,
  }).addTo(zipMap).bindTooltip(`ZIP ${location.postcode} search center`)

  for (const hotel of location.hotels ?? []) {
    const id = zipHotelId(hotel)
    const marker = L.marker([hotel.latitude, hotel.longitude], {
      icon: hotelMarkerIcon(id === selectedZipHotelId.value),
      title: hotel.name,
      alt: hotel.name,
    }).addTo(zipMap)
    marker.on('click', () => selectZipHotel(hotel))
    zipHotelMarkers.set(id, marker)
  }
  window.setTimeout(() => zipMap?.invalidateSize(), 0)
}, { flush: 'post' })

watch(selectedZipHotelId, (selectedId) => {
  for (const [id, marker] of zipHotelMarkers.entries()) {
    marker.setIcon(hotelMarkerIcon(id === selectedId))
  }
})

onBeforeUnmount(() => {
  clearZipHotelMarkers()
  zipCenterMarker?.remove()
  zipMap?.remove()
})

async function createBooking(item) {
  if (!authUser.value) {
    view.value = 'account'
    authMode.value = 'login'
    authError.value = 'Sign in before creating a demo booking.'
    return
  }
  busyBookingId.value = item.stay.trip_id
  bookingError.value = ''
  try {
    const booking = await api('/api/bookings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trip_id: item.stay.trip_id }),
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
  if (nextView === 'bookings' && !authUser.value) {
    view.value = 'account'
    authMode.value = 'login'
    authError.value = 'Sign in to view your booking history.'
    return
  }
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
        <div class="account-nav">
          <template v-if="authUser"><span>Hi, {{ authUser.username }}</span><button type="button" @click="logout">Log out</button></template>
          <button v-else type="button" @click="view = 'account'; authMode = 'login'; authError = ''">Sign in / Create account</button>
        </div>
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
        <section v-if="view === 'stays' || view === 'bookings'" class="search-card" aria-labelledby="search-title">
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
          <p v-if="authUser && resultsUserId === authUser.user_id && submittedQuery && searchState === 'ready'" class="search-frequency" role="status">Your matching searches today (UTC): {{ searchCount }}. A 20% demo surge starts at 4.</p>
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

        <section v-if="view === 'stays'" class="zip-card" aria-labelledby="zip-title">
          <div class="zip-heading">
            <p class="eyebrow">Location demo</p>
            <h2 id="zip-title">ZIP lookup demonstration</h2>
            <p class="zip-description">Check the demo postcode through the backend geocoder.</p>
          </div>
          <form class="zip-form" novalidate @submit.prevent="lookupZip">
            <label for="zip-postcode">ZIP code</label>
            <input id="zip-postcode" v-model="zipPostcode" type="text" inputmode="numeric" autocomplete="postal-code" maxlength="5" pattern="[0-9]{5}" placeholder="16802" required />
            <button class="secondary-button zip-button" type="submit" :disabled="zipState === 'loading'">
              {{ zipState === 'loading' ? 'Looking up…' : 'Look up ZIP' }}
            </button>
          </form>
          <p v-if="zipState === 'loading'" class="zip-status" role="status">Looking up ZIP {{ zipPostcode.trim() }}…</p>
          <p v-else-if="zipState === 'invalid'" class="notice error zip-message" role="alert">Invalid ZIP: {{ zipError }}</p>
          <p v-else-if="zipState === 'unresolved'" class="notice error zip-message" role="alert">ZIP not resolved: {{ zipError }}</p>
          <p v-else-if="zipState === 'failure'" class="notice error zip-message" role="alert">ZIP lookup failed: {{ zipError }}</p>
          <table v-else-if="zipLocation" class="zip-result" aria-label="ZIP location result">
            <caption>Location for {{ zipLocation.postcode }}</caption>
            <tbody>
              <tr><th scope="row">Postcode</th><td>{{ zipLocation.postcode }}</td></tr>
              <tr v-if="zipLocation.locality"><th scope="row">Locality</th><td>{{ zipLocation.locality }}</td></tr>
              <tr><th scope="row">Latitude</th><td>{{ zipLocation.latitude }}</td></tr>
              <tr><th scope="row">Longitude</th><td>{{ zipLocation.longitude }}</td></tr>
            </tbody>
          </table>
          <div v-if="zipLocation" class="zip-hotels">
            <h3>{{ zipSource === 'local' ? 'Saved locally' : 'API results' }}</h3>
            <p v-if="zipSource === 'local'" class="zip-empty">These are saved demo records for this ZIP, not a complete list of hotels in the area.</p>
            <p v-if="zipState === 'no-results'" class="zip-empty" role="status">
              {{ zipSource === 'local'
                ? `No saved hotels remain for ZIP ${zipLocation.postcode}. Look up the ZIP again to search API results.`
                : `ZIP resolved to ${zipLocation.locality || zipLocation.postcode}, but no nearby hotels were returned within 5 km.` }}
            </p>
            <div v-else class="zip-hotel-explorer">
              <div class="zip-hotel-list" role="list" aria-label="Hotels within 5 km">
                <article
                  v-for="hotel in zipLocation.hotels"
                  :key="zipHotelId(hotel)"
                  class="zip-hotel-entry"
                  role="listitem"
                >
                  <button
                    type="button"
                    class="zip-hotel-option"
                    :class="{ selected: selectedZipHotelId === zipHotelId(hotel) }"
                    :aria-pressed="selectedZipHotelId === zipHotelId(hotel)"
                    @click="selectZipHotel(hotel)"
                  >
                    <strong>{{ hotel.name || 'Hotel name unavailable' }}</strong>
                    <span>{{ hotel.locality || (zipSource === 'local' ? zipLocation.locality : '') || 'Locality unavailable' }}</span>
                    <small v-if="hotel.address">{{ hotel.address }}</small>
                    <small>Coordinates: {{ hotel.latitude }}, {{ hotel.longitude }}</small>
                    <small v-if="hotel.distance_meters != null">Distance from ZIP center: {{ distanceLabel(hotel.distance_meters) }}</small>
                  </button>
                  <div class="zip-hotel-actions">
                    <button
                      v-if="isHotelSaved(hotel)"
                      class="secondary-button zip-save-button"
                      type="button"
                      :disabled="isHotelPending(hotel)"
                      @click="removeHotelFromLocal(hotel)"
                    >{{ isHotelPending(hotel) ? 'Removing…' : 'Remove from Local' }}</button>
                    <button
                      v-else
                      class="secondary-button zip-save-button"
                      type="button"
                      :disabled="!hotel.provider_id || isHotelPending(hotel)"
                      :title="hotel.provider_id ? '' : 'This API result has no provider ID to save.'"
                      @click="addHotelToLocal(hotel)"
                    >{{ isHotelPending(hotel) ? 'Saving…' : 'Add to Local' }}</button>
                  </div>
                  <div v-if="zipSource === 'local' && hotel.nightly_rates?.length" class="demo-night-rates">
                    <strong>Simulated classroom rates and availability</strong>
                    <ul>
                      <li v-for="night in hotel.nightly_rates" :key="night.stay_date">
                        {{ dateLabel(night.stay_date) }} — {{ formatDemoRate(night.nightly_rate_cents) }} per night · {{ night.rooms_available }} rooms available
                      </li>
                    </ul>
                  </div>
                </article>
              </div>
              <div ref="zipMapElement" class="zip-map" role="application" :aria-label="`Map of hotels near ZIP ${zipLocation.postcode}`"></div>
            </div>
            <p v-if="zipActionFeedback.text" :class="['zip-action-feedback', zipActionFeedback.type === 'error' ? 'error' : 'success']" :role="zipActionFeedback.type === 'error' ? 'alert' : 'status'">
              {{ zipActionFeedback.text }}
            </p>
            <p v-if="selectedZipHotel" class="zip-map-selection" role="status">
              Selected hotel: {{ selectedZipHotel.name }} — highlighted in the list and on the map.
            </p>
          </div>
        </section>

        <p v-if="notice" class="notice success" role="status">{{ notice }}</p>
        <p v-if="bookingError" class="notice error" role="alert">{{ bookingError }}</p>

        <section v-if="view === 'account'" class="account-card" aria-labelledby="account-title">
          <p class="eyebrow">Your demo account</p>
          <h2 id="account-title">{{ authMode === 'login' ? 'Sign in' : 'Create an account' }}</h2>
          <p>Use made-up demo credentials only. No real reservation or payment is made.</p>
          <form class="account-form" @submit.prevent="submitAccount">
            <label>Username<input v-model.trim="authUsername" autocomplete="username" required minlength="3" maxlength="30" /></label>
            <label v-if="authMode === 'register'">Display name (optional)<input v-model.trim="authDisplayName" autocomplete="nickname" maxlength="80" /></label>
            <label>Password<input v-model="authPassword" type="password" :autocomplete="authMode === 'login' ? 'current-password' : 'new-password'" required minlength="8" /></label>
            <p v-if="authError" class="notice error" role="alert">{{ authError }}</p>
            <button class="primary-button" type="submit" :disabled="authBusy">{{ authBusy ? 'Please wait…' : authMode === 'login' ? 'Sign in' : 'Create account' }}</button>
          </form>
          <button class="text-button" type="button" @click="authMode = authMode === 'login' ? 'register' : 'login'; authError = ''; notice = ''">{{ authMode === 'login' ? 'New here? Create a demo account' : 'Already have an account? Sign in' }}</button>
          <p class="demo-hint">Seeded demo: username <code>demo1</code>, password <code>DemoPass123!</code>.</p>
        </section>

        <template v-else-if="view === 'stays'">
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
                  <span>Displayed nightly rate</span><strong>{{ money(item.pricing.displayed_nightly_rate_usd) }}</strong><small>per night</small>
                  <span v-if="item.pricing.surge_applied" class="surge-note">20% demo surge · base {{ money(item.pricing.base_nightly_rate_usd) }}</span>
                  <p>{{ stayTotal(item) }} stay total*</p>
                  <button class="primary-button" type="button" :disabled="busyBookingId === item.stay.trip_id" @click="createBooking(item)">{{ busyBookingId === item.stay.trip_id ? 'Booking…' : 'Book this stay' }}</button>
                </div>
              </article>
            </div>
            <p v-if="filteredResults.length" class="price-disclaimer">* Simulated total is displayed nightly rate × nights. For signed-in users, the fourth matching hotel-name search in a UTC day raises the displayed rate by 20% once. This classroom urgency assumption is not evidence of actual urgency. Base rates stay unchanged; taxes, fees, inventory, and payment are not included.</p>
          </template>
        </template>

        <section v-else class="history-section" aria-labelledby="history-title">
          <div class="section-head"><div><p class="eyebrow">Your demo trips</p><h2 id="history-title">Booking history</h2></div><span v-if="bookingState === 'ready'" class="result-count">{{ bookings.length }} booking{{ bookings.length === 1 ? '' : 's' }}</span></div>
          <p class="history-intro">Bookings for {{ authUser?.username }} are stored locally. Cancelling keeps a record in history.</p>
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
    <TravelChat />
    <footer class="site-footer">Expedia Rep · classroom prototype · simulated bookings only</footer>
  </div>
</template>
