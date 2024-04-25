// logout.js

// Function to send a logout request to the server
function sendLogoutRequest() {
    fetch('/logout', {
        method: 'POST',
        credentials: 'same-origin',  // Include cookies in the request
    })
    .then(response => {
        if (response.ok) {
            console.log('Logged out successfully');
        } else {
            console.error('Failed to logout');
        }
    })
    .catch(error => {
        console.error('Error during logout:', error);
    });
}

// Event listener to detect when the user closes the browser/tab
window.addEventListener('unload', function (e) {
    sendLogoutRequest();
});


// FOR PFT RELATED SITES

// ADD IN <HEAD>
// <script src="{{ url_for('static', filename='logout.js') }}"></script>
// <script>
//     // JavaScript function to navigate back to the previous page
//      function goBack() {
//          window.history.back();
//    }
// </script>
// <input type="button" onclick="goBack()" value="Back">