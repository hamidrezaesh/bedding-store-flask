function decrement(btn) {
    const input = btn.parentElement.querySelector('.quantity-input');
    let value = parseInt(input.value);
    const min = parseInt(input.min) || 1;
    if (value > min) {
        input.value = value - 1;
    }
}

function increment(btn) {
    const input = btn.parentElement.querySelector('.quantity-input');
    let value = parseInt(input.value);
    const max = parseInt(input.max) || 999;
    if (value < max) {
        input.value = value + 1;
    }
}