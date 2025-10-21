package paymentSystem;

public class UPIPaymentProcessor  implements PaymentProcessor {

    @Override
    public void pay(double amount) {
      
        System.out.println("amount being paid using UPI: " + amount );
       
    }
    
}
