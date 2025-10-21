package paymentSystem;

public class CreditCardPaymentProcessor  implements PaymentProcessor {

    @Override
    public void pay(double amount) {
        System.out.println("amount being paid using Credit Card: " + amount );
    }
    
}



    

