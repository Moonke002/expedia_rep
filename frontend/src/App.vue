<script setup>
import { computed, ref } from 'vue'

const hotelName = ref('')
const results = ref([])
const state = ref('idle')
const errorMessage = ref('')
const selectedCity = ref('all')
const selectedPrice = ref('all')

const cityOptions = computed(() => {
  const cities = new Set(results.value.map((result) => result.hotel?.city).filter(Boolean))
  return [...cities].sort()
})

const priceOptions = computed(() => {
  const rates = new Set(
    results.value
      .map((result) => Number(result.hotel?.nightly_rate_usd))
      .filter((rate) => Number.isFinite(rate)),
  )
  return [...rates].sort((left, right) => left - right)
})

const filteredResults = computed(() => {
  return results.value.filter((result) => {
    const hotel = result.hotel ?? {}
    const cityMatches = selectedCity.value === 'all' || hotel.city === selectedCity.value
    const price = Number(hotel.nightly_rate_usd)
    const priceMatches =
      selectedPrice.value === 'all' ||
      (Number.isFinite(price) && price <= Number(selectedPrice.value))
    return cityMatches && priceMatches
  })
})

const resultLabel = computed(() => {
  const count = filteredResults.value.length
  return `${count} available stay${count === 1 ? '' : 's'}`
})

async function searchHotels() {
  const query = hotelName.value.trim()
  selectedCity.value = 'all'
  selectedPrice.value = 'all'

  if (!query) {
    results.value = []
    state.value = 'idle'
    errorMessage.value = ''
    return
  }

  state.value = 'loading'
  errorMessage.value = ''

  try {
    const response = await fetch(`/api/hotels/search?hotel_name=${encodeURIComponent(query)}`)
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.detail ?? 'The search could not be completed.')

    results.value = payload.results
    state.value = results.value.length ? 'results' : 'empty'
  } catch (error) {
    results.value = []
    errorMessage.value = error instanceof Error ? error.message : 'The search could not be completed.'
    state.value = 'error'
  }
}

function formatDate(date) {
  if (!date) return 'Date unavailable'
  const parsedDate = new Date(`${date}T00:00:00`)
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(parsedDate)
}

function stayNights(stay) {
  const checkIn = new Date(`${stay.check_in}T00:00:00`)
  const checkOut = new Date(`${stay.check_out}T00:00:00`)
  const nights = Math.round((checkOut - checkIn) / 86400000)
  return Number.isFinite(nights) && nights > 0 ? nights : null
}

function formatCurrency(value) {
  const amount = Number(value)
  return Number.isFinite(amount)
    ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount)
    : '—'
}

function stayTotal(result) {
  const nightlyRate = Number(result.hotel?.nightly_rate_usd)
  const nights = stayNights(result.stay ?? {})
  return Number.isFinite(nightlyRate) && nights ? nightlyRate * nights : null
}

function resetFilters() {
  selectedCity.value = 'all'
  selectedPrice.value = 'all'
}
</script>

<template>
  <main class="app-shell">
    <header class="site-header">
      <a class="brand" href="#page-title" aria-label="Expedia Rep home">expedia<span>rep</span></a>
      <p class="header-note">Stay search prototype</p>
    </header>

    <section class="trip-header" aria-labelledby="page-title">
      <button class="back-button" type="button" aria-label="Go back" @click="hotelName = ''">
        <span aria-hidden="true">←</span>
      </button>
      <div>
        <p class="eyebrow">Hotel results</p>
        <h1 id="page-title">Choose stay</h1>
        <p class="trip-summary">Sep 18 – Sep 20 <span aria-hidden="true">·</span> 1 room, 2 travelers</p>
      </div>
    </section>

    <section class="search-panel" aria-labelledby="search-title">
      <div class="search-heading">
        <div>
          <p class="eyebrow">Search the supplied data</p>
          <h2 id="search-title">Where do you want to stay?</h2>
        </div>
        <span class="data-badge">CSV-backed</span>
      </div>
      <form class="search-form" @submit.prevent="searchHotels">
        <label for="hotel-name">Hotel name</label>
        <div class="search-controls">
          <span class="search-icon" aria-hidden="true">⌕</span>
          <input
            id="hotel-name"
            v-model="hotelName"
            type="search"
            name="hotel-name"
            placeholder="Search by hotel name"
            autocomplete="off"
          />
          <button type="submit" :disabled="state === 'loading'">
            {{ state === 'loading' ? 'Searching…' : 'Search' }}
          </button>
        </div>
      </form>
    </section>

    <p v-if="state === 'error'" class="message error" role="alert">{{ errorMessage }}</p>
    <p v-else-if="state === 'empty'" class="message" role="status">
      No matching hotel stays were found.
    </p>
    <p v-else-if="state === 'idle'" class="message hint" role="status">
      Search for a supplied hotel to see available fixed-date stays.
    </p>

    <section v-else-if="state === 'results'" class="results-section" aria-labelledby="results-title">
      <div class="filter-bar">
        <div class="filter-label"><span aria-hidden="true">☷</span> Filter stays</div>
        <label class="filter-control">
          <span class="sr-only">City</span>
          <select v-model="selectedCity" aria-label="Filter by city">
            <option value="all">All cities</option>
            <option v-for="city in cityOptions" :key="city" :value="city">{{ city }}</option>
          </select>
        </label>
        <label class="filter-control">
          <span class="sr-only">Nightly price</span>
          <select v-model="selectedPrice" aria-label="Filter by nightly price">
            <option value="all">Any price</option>
            <option v-for="price in priceOptions" :key="price" :value="price">
              Up to {{ formatCurrency(price) }}/night
            </option>
          </select>
        </label>
        <button
          v-if="selectedCity !== 'all' || selectedPrice !== 'all'"
          class="reset-button"
          type="button"
          @click="resetFilters"
        >
          Clear filters
        </button>
      </div>

      <div class="results-heading">
        <div>
          <p class="eyebrow">Available stays</p>
          <h2 id="results-title">Hotels matching “{{ hotelName }}”</h2>
        </div>
        <span class="result-count">{{ resultLabel }}</span>
      </div>

      <p v-if="!filteredResults.length" class="message" role="status">
        No stays match the selected filters.
      </p>

      <div v-else class="stay-list">
        <article v-for="(result, index) in filteredResults" :key="`${result.stay.trip_id}-${index}`" class="stay-card">
          <div class="stay-image" :class="`tone-${index % 4}`" role="img" :aria-label="`${result.hotel.hotel_name} photo placeholder`">
            <span>{{ result.hotel.hotel_id }}</span>
            <small>Hotel photo</small>
          </div>
          <div class="stay-details">
            <div class="stay-copy">
              <p class="stay-kicker">Available stay · {{ result.stay.trip_id }}</p>
              <h3>{{ result.hotel.hotel_name }}</h3>
              <p class="location">{{ result.hotel.city }}, {{ result.hotel.state }}</p>
              <p class="trip-name">{{ result.stay.trip_name }}</p>
              <p class="dates">
                <span aria-hidden="true">▣</span>
                {{ formatDate(result.stay.check_in) }} – {{ formatDate(result.stay.check_out) }}
                <span v-if="stayNights(result.stay)"> · {{ stayNights(result.stay) }} nights</span>
              </p>
            </div>
            <div class="price-module">
              <span class="price-label">Nightly rate</span>
              <strong>{{ formatCurrency(result.hotel.nightly_rate_usd) }}</strong>
              <span v-if="stayTotal(result)" class="total-label">
                {{ formatCurrency(stayTotal(result)) }} stay total
              </span>
              <span class="price-note">Savings unavailable in supplied data</span>
            </div>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>
