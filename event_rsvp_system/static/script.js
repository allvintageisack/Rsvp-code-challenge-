const rsvpButton = document.getElementById('rsvpButton');
const messageDiv = document.getElementById('message');
const guestInfoDiv = document.getElementById('guestInfo');
const guestNameSpan = document.getElementById('guestName');
const guestEmailSpan = document.getElementById('guestEmail');

let uniqueId = null; // This will hold the unique ID from the URL

// Function to extract query parameters from the URL
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

// --- Initial Load ---
document.addEventListener('DOMContentLoaded', () => {
    uniqueId = getQueryParam('id'); // Get the unique ID from '?id=...'

    if (!uniqueId) {
        // If no ID, display an error message and disable the button
        displayMessage('Invalid invitation link. Please check your email.', 'error');
        rsvpButton.disabled = true;
        return;
    }

    displayMessage('Loading your details...', 'info');
    rsvpButton.disabled = true; // Disable until we know guest status

    // Fetch guest status and details from the backend
    fetch(`/api/guest_status?id=${uniqueId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                guestNameSpan.textContent = data.guest_name || 'Guest';
                guestEmailSpan.textContent = data.guest_email || '';
                guestInfoDiv.style.display = 'block';

                if (data.rsvp_status === 'confirmed') {
                    displayMessage('You have already confirmed your spot. We look forward to seeing you!', 'info');
                    rsvpButton.textContent = 'Already Confirmed!';
                    rsvpButton.disabled = true;
                } else if (data.rsvp_status === 'declined') {
                    displayMessage('You have previously declined. Please contact us if you wish to change your RSVP.', 'info');
                    rsvpButton.textContent = 'Previously Declined';
                    rsvpButton.disabled = true;
                } else if (data.rsvp_status === 'waitlisted') {
                     displayMessage('You are currently on the waitlist. We will notify you if a spot becomes available.', 'info');
                     rsvpButton.textContent = 'On Waitlist';
                     rsvpButton.disabled = true;
                }
                else {
                    displayMessage('Click "Confirm My Spot!" to RSVP.', 'info');
                    rsvpButton.disabled = false;
                }
            } else {
                displayMessage(data.message || 'Error loading guest details. Invalid link or guest not found.', 'error');
                rsvpButton.disabled = true;
            }
        })
        .catch(error => {
            console.error('Error fetching guest status:', error);
            displayMessage('Could not load guest details. Please try again later.', 'error');
            rsvpButton.disabled = true;
        });
});

// --- RSVP Button Click Handler ---
rsvpButton.addEventListener('click', async () => {
    if (!uniqueId) {
        displayMessage('No invitation ID found.', 'error');
        return;
    }

    rsvpButton.disabled = true; // Prevent double clicks
    rsvpButton.textContent = 'Confirming...';
    displayMessage('Processing your reservation...', 'info');

    try {
        const response = await fetch('/api/rsvp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ unique_id: uniqueId, action: 'confirm' }), // We can add 'decline' later
        });

        const data = await response.json();

        if (response.ok) { // Check if HTTP status is 2xx
            if (data.status === 'success') {
                displayMessage(data.message || 'Your spot has been successfully confirmed!', 'success');
                rsvpButton.textContent = 'Spot Confirmed!';
            } else if (data.status === 'waitlisted') {
                displayMessage(data.message || 'Event is full. You have been added to the waitlist.', 'info');
                rsvpButton.textContent = 'Added to Waitlist!';
            }
            else {
                displayMessage(data.message || 'Failed to confirm your spot. Please try again.', 'error');
                rsvpButton.textContent = 'Try Again';
                rsvpButton.disabled = false;
            }
        } else {
            // Handle HTTP errors (e.g., 400, 500)
            displayMessage(data.message || 'An error occurred during reservation. Please try again.', 'error');
            rsvpButton.textContent = 'Try Again';
            rsvpButton.disabled = false;
        }
    } catch (error) {
        console.error('Error during fetch:', error);
        displayMessage('Network error or server unavailable. Please try again.', 'error');
        rsvpButton.textContent = 'Try Again';
        rsvpButton.disabled = false;
    }
});

// Helper function to display messages
function displayMessage(msg, type) {
    messageDiv.textContent = msg;
    messageDiv.className = 'message-div'; // Reset classes
    messageDiv.classList.add('message-' + type);
}