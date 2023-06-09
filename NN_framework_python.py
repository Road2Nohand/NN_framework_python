import numpy as np

# Spiral-Trainingsdaten mit Klassenlabels
def spiral_data(points, classes):
    X = np.zeros((points*classes, 2))
    y = np.zeros(points*classes, dtype='uint8')
    for class_number in range(classes):
        ix = range(points*class_number, points*(class_number+1))
        r = np.linspace(0.0, 1, points)  # radius
        t = np.linspace(class_number*4, (class_number+1)*4, points) + np.random.randn(points)*0.2
        X[ix] = np.c_[r*np.sin(t*2.5), r*np.cos(t*2.5)]
        y[ix] = class_number
    return X, y


# Dense layer
class Layer_Dense:
    # Layer initialization
    def __init__(self, n_inputs, n_neurons):
        # Initialize weights and biases
        self.weights = 0.01 * np.random.randn(n_inputs, n_neurons)
        self.biases = np.zeros((1, n_neurons))
    # Forward pass
    def forward(self, inputs):
        # Remember input values
        self.inputs = inputs
        # Calculate output values from inputs, weights and biases
        self.output = np.dot(inputs, self.weights) + self.biases
    # Backward pass
    def backward(self, dvalues):
        # Gradients on parameters
        self.dweights = np.dot(self.inputs.T, dvalues)
        self.dbiases = np.sum(dvalues, axis=0, keepdims=True)
        # Gradient on values
        self.dinputs = np.dot(dvalues, self.weights.T)

# ReLU activation
class Activation_ReLU:
    # Forward pass
    def forward(self, inputs):
        # Remember input values
        self.inputs = inputs
        # Calculate output values from inputs
        self.output = np.maximum(0, inputs)
    # Backward pass
    def backward(self, dvalues):
        # Since we need to modify original variable,
        # let's make a copy of values first
        self.dinputs = dvalues.copy()
        # Zero gradient where input values were negative
        self.dinputs[self.inputs <= 0] = 0

# Softmax activation
class Activation_Softmax:
    # Forward pass
    def forward(self, inputs):
        # Remember input values
        self.inputs = inputs
        # Get unnormalized probabilities
        exp_values = np.exp(inputs - np.max(inputs, axis=1,keepdims=True))
        # Normalize them for each sample
        probabilities = exp_values / np.sum(exp_values, axis=1,keepdims=True)
        self.output = probabilities
    """# Backward pass
    def backward(self, dvalues):
        # Create uninitialized array
        self.dinputs = np.empty_like(dvalues)
        # Enumerate outputs and gradients
        for index, (single_output, single_dvalues) in enumerate(zip(self.output, dvalues)):
            # Flatten output array
            single_output = single_output.reshape(-1, 1)
            # Calculate Jacobian matrix of the output
            jacobian_matrix = np.diagflat(single_output) - np.dot(single_output, single_output.T)
            # Calculate sample-wise gradient
            # and add it to the array of sample gradients
            self.dinputs[index] = np.dot(jacobian_matrix,single_dvalues)"""

# Common loss class
class Loss:
    # Calculates the data and regularization losses
    # given model output and ground truth values
    def calculate(self, output, y):
        # Calculate sample losses
        sample_losses = self.forward(output, y)
        # Calculate mean loss
        data_loss = np.mean(sample_losses)
        # Return loss
        return data_loss

# Cross-entropy loss
class Loss_CategoricalCrossentropy(Loss):
    # Forward pass
    def forward(self, y_pred, y_true):
        # Number of samples in a batch
        samples = len(y_pred)
        # Clip data to prevent division by 0
        # Clip both sides to not drag mean towards any value
        y_pred_clipped = np.clip(y_pred, 1e-7, 1 - 1e-7)
        # Probabilities for target values -
        # only if categorical labels
        if len(y_true.shape) == 1:
            correct_confidences = y_pred_clipped[range(samples),y_true]
        # Mask values - only for one-hot encoded labels
        elif len(y_true.shape) == 2:
            correct_confidences = np.sum(y_pred_clipped * y_true,axis=1)
        # Losses
        negative_log_likelihoods = -np.log(correct_confidences)
        return negative_log_likelihoods
    # Backward pass
    def backward(self, dvalues, y_true):
        # Number of samples
        samples = len(dvalues)
        # Number of labels in every sample
        # We'll use the first sample to count them
        labels = len(dvalues[0])
        # If labels are sparse, turn them into one-hot vector
        if len(y_true.shape) == 1:
            y_true = np.eye(labels)[y_true]
        # Calculate gradient
        self.dinputs = -y_true / dvalues
        # Normalize gradient
        self.dinputs = self.dinputs / samples


# Softmax classifier - combined Softmax activation
# and cross-entropy loss for faster backward step
class Activation_Softmax_Loss_CategoricalCrossentropy():
    # Creates activation and loss function objects
    def __init__(self):
        self.activation = Activation_Softmax()
        self.loss = Loss_CategoricalCrossentropy()
    # Forward pass
    def forward(self, inputs, y_true):
        # Output layer's activation function
        self.activation.forward(inputs)
        # Set the output
        self.output = self.activation.output
        # Calculate and return loss value
        return self.loss.calculate(self.output, y_true)
    # Backward pass
    def backward(self, dvalues, y_true):
        # Number of samples
        samples = len(dvalues)
        # If labels are one-hot encoded,
        # turn them into discrete values
        if len(y_true.shape) == 2:
            y_true = np.argmax(y_true, axis=1)
        # Copy so we can safely modify
        self.dinputs = dvalues.copy()
        # Calculate gradient
        self.dinputs[range(samples), y_true] -= 1
        # Normalize gradient
        self.dinputs = self.dinputs / samples


class Optimizer_SGD_without_lrDecay_and_Momentum:
    def __init__(self, learning_rate=1.0):
        self.learning_rate = learning_rate
    # Update parameters
    def update_params(self, layer):
        layer.weights += -self.learning_rate * layer.dweights
        layer.biases += -self.learning_rate * layer.dbiases


class Optimizer_SGD_lrDecay:
    def __init__(self, lr=1, decayRate=0):
        self.lr = lr
        self.current_lr = lr
        self.decayRate = decayRate
        self.step = 0

    # wird einmal vor jeder Backpropagation ausgeführt
    def update_lr(self):
        if self.decayRate: # falls man "0" hat, macht ist die lr quasi steady und decay ist deaktiviert
            self.current_lr = self.lr * (1. / (1. + self.decayRate * self.step))

    # Weights und Biases einer Schicht updaten
    def update_params(self, layer):
        layer.weights += -self.current_lr * layer.dweights
        layer.biases += -self.current_lr * layer.dbiases

    def update_step(self):
        self.step += 1


class Optimizer_SGDmomentum:
    def __init__(self, lr=1, decayRate=0, momentum=0):
        self.lr = lr
        self.current_lr = lr
        self.decayRate = decayRate
        self.step = 0
        self.momentum = momentum # neuer HyperParameter

    # wird einmal vor jeder Backpropagation ausgeführt
    def update_lr(self):
        if self.decayRate: # falls man "0" hat, macht ist die lr quasi steady und decay ist deaktiviert
            self.current_lr = self.lr * (1. / (1. + self.decayRate * self.step))

    # Weights und Biases einer Schicht updaten
    def update_params(self, layer):

        if self.momentum:
            # wenn ein layer keine weight_momentums hat erstellen mit Nullen:
            if not hasattr(layer, "weight_momentums"):
                layer.weight_momentums = np.zeros_like(layer.weights)
                #wenn die nicht für weights gibt, auch nicht für biases:
                layer.bias_momentums = np.zeros_like(layer.biases)
        
            # Weights Momentums
            weight_updates = self.momentum * layer.weight_momentums -(self.current_lr * layer.dweights)
            layer.weight_momentums = weight_updates #übergabe für nächste Epoche

            # Biases Momentums
            bias_updates = self.momentum * layer.bias_momentums -(self.current_lr * layer.dbiases)
            layer.bias_momentums = bias_updates #übergabe für nächste Epoche

        else: #falls kein momentum und nur lr und aktueller Gradient
            weight_updates = -self.current_lr * layer.dweights
            bias_updates = -self.current_lr * layer.dbiases

        layer.weights += weight_updates
        layer.biases += bias_updates

    def update_step(self):
        self.step += 1

    
class Optimizer_AdaGrad:
    def __init__(self, lr=1, decayRate=0, epsilon=1e-7):
        self.lr = lr
        self.current_lr = lr
        self.decayRate = decayRate
        self.step = 0
        # self.momentum = momentum # alter HyperParameter
        self.epsilon = epsilon # neuer HyperParameter

    # wird einmal vor jeder Backpropagation ausgeführt
    def update_lr(self):
        if self.decayRate: # falls man "0" hat, macht ist die lr quasi steady und decay ist deaktiviert
            self.current_lr = self.lr * (1. / (1. + self.decayRate * self.step))

    # Weights und Biases einer Schicht updaten
    def update_params(self, layer):

        # statt weight_momentums, machen wir nun parm_caches
        if not hasattr(layer, "weight_cache"):
            layer.weight_cache = np.zeros_like(layer.weights)
            layer.bias_cache = np.zeros_like(layer.biases)
    
        # Update Cache mit Current Gradient^2
        layer.weight_cache += layer.dweights ** 2
        layer.bias_cache += layer.dbiases ** 2

        # Normalisierung der Updates dieser Epoche mit Cache Historie
        layer.weights += -self.current_lr * layer.dweights / (np.sqrt(layer.weight_cache) + self.epsilon)
        layer.biases += -self.current_lr * layer.dbiases / (np.sqrt(layer.bias_cache) + self.epsilon)

    def update_step(self):
        self.step += 1



class Optimizer_RMSProp:
    def __init__(self, lr=0.001, decayRate=0, epsilon=1e-7, rho=0.9):
        self.lr = lr
        self.current_lr = lr
        self.decayRate = decayRate
        self.step = 0
        self.epsilon = epsilon # neuer HyperParameter
        self.rho = rho

    # 1/t LR Decay
    def update_lr(self):
        if self.decayRate: # falls man "0" hat, macht ist die lr quasi steady und decay ist deaktiviert
            self.current_lr = self.lr * (1. / (1. + self.decayRate * self.step))

    # Weights und Biases einer Schicht updaten
    def update_params(self, layer):

        # Cache 0 Instanziierung
        if not hasattr(layer, "weight_cache"):
            layer.weight_cache = np.zeros_like(layer.weights)
            layer.bias_cache = np.zeros_like(layer.biases)
    
        # Update Cache mit Current Gradient^2 und rho
        layer.weight_cache = self.rho * layer.weight_cache + (1 -self.rho) * (layer.dweights ** 2)
        layer.bias_cache = self.rho * layer.bias_cache + (1 -self.rho) * (layer.dbiases ** 2)

        # Normalisierung der Updates dieser Epoche mit Cache und AdaGrad Bruch-Verfahren
        layer.weights += -self.current_lr * layer.dweights / (np.sqrt(layer.weight_cache) + self.epsilon)
        layer.biases += -self.current_lr * layer.dbiases / (np.sqrt(layer.bias_cache) + self.epsilon)

    def update_step(self):
        self.step += 1


class Optimizer_Adam:
    def __init__(self, lr=0.001, decayRate=0, epsilon=1e-7, beta1=0.9, beta2=0.999):
        self.lr = lr
        self.current_lr = lr
        self.decayRate = decayRate
        self.step = 0
        self.epsilon = epsilon # neuer HyperParameter
        self.beta1 = beta1
        self.beta2 = beta2

    # 1/t LR Decay
    def update_lr(self):
        if self.decayRate: # falls man "0" hat, macht ist die lr quasi steady und decay ist deaktiviert
            self.current_lr = self.lr * (1. / (1. + self.decayRate * self.step))

    # Weights und Biases eines Layers updaten
    def update_params(self, layer):

        # Cache 0-Initialisierung
        if not hasattr(layer, "weight_cache"):
            # wie bei RMSProp Cache
            layer.weight_cache = np.zeros_like(layer.weights)
            layer.bias_cache = np.zeros_like(layer.biases)
            # wie bei SGD Momentums
            layer.weight_momentums = np.zeros_like(layer.weights)
            layer.bias_momentums = np.zeros_like(layer.biases)
    
        # Update Momentum mit Current Gradients und beta1's anstatt rho wie bei RMSProp
        layer.weight_momentums = self.beta1 * layer.weight_cache + (1 -self.beta1) * layer.dweights
        layer.bias_momentums = self.beta1 * layer.bias_cache + (1 -self.beta1) * layer.dbiases

        # Momentums korrigieren/anheizen mit 1 - beta^step, nach ca. 50 Steps normal groß, bei erster Epoche 10x 
        weight_momentums_corrected = layer.weight_momentums / (1 -self.beta1 **(self.step+1)) # + 1 weil in der ersten Epoche "0"
        bias_momentums_corrected =  layer.bias_momentums / (1 -self.beta1 **(self.step+1))

        # Update Cache mit Squared Current Gradients wie bei AdaGrad und beta2 anstatt rho wie bei RMSProp
        layer.weight_cache = self.beta2 * layer.weight_cache + (1 - self.beta2) * layer.dweights**2
        layer.bias_cache = self.beta2 * layer.bias_cache + (1 - self.beta2) * layer.dbiases**2

        # Cache korrigieren/anheizen mit beta2 wird wesentlich stärker als Momentums angeheizt! 1000x in der ersten Epoche
        # Erst in der 5000. Epoche normal "1"
        # Der Cache ist für die Normalisierung der Updates der Parameter zuständig, Am Anfang wird sehr stark normalisiert!
        # Am Ende muss nicht mehr so stark normalisiert werden und Parameter-Updates dürfen überproportional werden
        weight_cache_corrected = layer.weight_cache / (1 -self.beta2 **(self.step+1))
        bias_cache_corrected = layer.bias_cache / (1 -self.beta2 **(self.step+1))

        # Vanilla SGD Parameter Update und Normalisierung
        # Mit Square Root Cache vom AdaGrad Bruch-Verfahren
        layer.weights += -self.current_lr * weight_momentums_corrected / (np.sqrt(weight_cache_corrected) + self.epsilon)
        layer.biases += -self.current_lr * bias_momentums_corrected / (np.sqrt(bias_cache_corrected) + self.epsilon)

    def update_step(self):
        self.step += 1





X, y = spiral_data(100, 3)
dense1 = Layer_Dense(2, 64)
activation1 = Activation_ReLU()
dense2 = Layer_Dense(64, 3)
loss_activation = Activation_Softmax_Loss_CategoricalCrossentropy()
optimizer = Optimizer_Adam(decayRate=0.000001, lr=0.05)

for epoch in range(20001): # 10.000 Epochen
    # Forward Pass
    dense1.forward(X)
    activation1.forward(dense1.output)
    dense2.forward(activation1.output)
    # loss
    loss = loss_activation.forward(dense2.output, y)

    # Akkuranz in %
    predictions = np.argmax(loss_activation.output, axis=1) #index vom größten Wert in einem Sample
    accuracy = np.mean(predictions==y)

    # bei jedem 100er Schritt Ausgabe
    if not epoch % 100:
        print(f'epoch: {epoch}', f'acc: {accuracy:.3f}', f'loss: {loss:.3f}', f'lr: {optimizer.current_lr}')

    # Backward Pass
    loss_activation.backward(loss_activation.output, y)
    dense2.backward(loss_activation.dinputs)
    activation1.backward(dense2.dinputs)
    dense1.backward(activation1.dinputs)

    # Update weights and biases
    optimizer.update_lr()
    optimizer.update_params(dense1)
    optimizer.update_params(dense2)
    optimizer.update_step()