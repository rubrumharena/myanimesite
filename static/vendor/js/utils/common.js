export function humanizeNumber(value) {
    if (value >= 1000 && value < 1_000_000) {
        return (Math.floor(value / 100) / 10).toString().replace('.', ',') + ' тыс.';
    } else if (value < 1000) {
        return value.toString();
    } else {
        return (Math.floor(value / 100000) / 10).toString().replace('.', ',') + ' мил.';
    }
}